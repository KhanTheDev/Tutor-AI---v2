"""Tutor AI Platform - Flask JSON API entry point.

Serves no HTML. The frontend is a separate static site (deployed on
Netlify) that calls these endpoints directly.
"""

import logging

from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import text
from werkzeug.exceptions import RequestEntityTooLarge
import config
from models import ChatMessage, Course, Document, db
from services.document_processor import allowed_file, get_file_type, process_document_file
from services.embedding_service import (
    EmbeddingServiceError,
    add_document_chunks,
    delete_document_chunks,
)
from services.tutor_service import TutorServiceError, answer_question

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY

    if not config.SQLALCHEMY_DATABASE_URI:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set it to a Postgres connection "
            "string with the pgvector extension available (e.g. a free Neon database)."
        )
    app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

    CORS(app, resources={r"/api/*": {"origins": config.ALLOWED_ORIGINS}})

    db.init_app(app)

    with app.app_context():
        db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.session.commit()
        db.create_all()

    register_routes(app)
    register_error_handlers(app)

    return app


def serialize_course(course: Course) -> dict:
    return {
        "id": course.id,
        "name": course.name,
        "description": course.description,
        "document_count": course.document_count,
        "ready_document_count": course.ready_document_count,
        "created_at": course.created_at.isoformat(),
    }


def serialize_document(document: Document) -> dict:
    return {
        "id": document.id,
        "original_filename": document.original_filename,
        "file_type": document.file_type,
        "status": document.status,
        "total_pages": document.total_pages,
        "total_chunks": document.total_chunks,
        "upload_date": document.upload_date.isoformat(),
    }


def serialize_message(message: ChatMessage) -> dict:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "sources": message.get_sources(),
        "created_at": message.created_at.isoformat(),
    }


def register_routes(app: Flask) -> None:
    @app.route("/api/courses", methods=["GET"])
    def list_courses():
        courses = Course.query.order_by(Course.created_at.desc()).all()
        return jsonify({"success": True, "courses": [serialize_course(c) for c in courses]})

    @app.route("/api/courses", methods=["POST"])
    def create_course():
        payload = request.get_json(silent=True) or {}
        name = (payload.get("name") or "").strip()
        description = (payload.get("description") or "").strip()

        if not name:
            return jsonify({"success": False, "error": "Course name is required."}), 400

        course = Course(name=name, description=description or None)
        db.session.add(course)
        db.session.commit()

        return jsonify({"success": True, "course": serialize_course(course)}), 201

    @app.route("/api/courses/<int:course_id>", methods=["GET"])
    def course_detail(course_id: int):
        course = Course.query.get_or_404(course_id)
        documents = (
            Document.query.filter_by(course_id=course_id)
            .order_by(Document.upload_date.desc())
            .all()
        )
        messages = (
            ChatMessage.query.filter_by(course_id=course_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(config.CHAT_HISTORY_LIMIT)
            .all()
        )
        return jsonify(
            {
                "success": True,
                "course": serialize_course(course),
                "documents": [serialize_document(d) for d in documents],
                "messages": [serialize_message(m) for m in messages],
            }
        )

    @app.route("/api/courses/<int:course_id>", methods=["DELETE"])
    def delete_course(course_id: int):
        course = Course.query.get_or_404(course_id)

        for document in course.documents:
            try:
                delete_document_chunks(document.id)
            except EmbeddingServiceError:
                logger.exception(
                    "Failed to delete chunks for document %s during course deletion",
                    document.id,
                )

        db.session.delete(course)
        db.session.commit()

        return jsonify({"success": True})

    @app.route("/api/courses/<int:course_id>/upload", methods=["POST"])
    def upload_document(course_id: int):
        course = Course.query.get_or_404(course_id)

        if "document" not in request.files:
            return jsonify({"success": False, "error": "No file was selected."}), 400

        file = request.files["document"]
        if not file or not file.filename:
            return jsonify({"success": False, "error": "No file was selected."}), 400

        original_filename = file.filename
        if not allowed_file(original_filename):
            return jsonify(
                {"success": False, "error": "Only PDF, TXT, JPG, and PNG files are supported."}
            ), 400

        file_type = get_file_type(original_filename)
        file_bytes = file.read()

        document = Document(
            course_id=course.id,
            original_filename=original_filename,
            file_type=file_type,
            status="processing",
        )
        db.session.add(document)
        db.session.commit()

        try:
            chunks, total_pages = process_document_file(
                file_bytes=file_bytes,
                file_type=file_type,
                course_id=course.id,
                document_id=document.id,
                document_name=original_filename,
            )

            add_document_chunks(chunks)

            document.status = "ready"
            document.total_pages = total_pages
            document.total_chunks = len(chunks)
            db.session.commit()

            return jsonify({"success": True, "document": serialize_document(document)}), 201
        except EmbeddingServiceError as exc:
            logger.exception("Embedding failure during upload")
            _mark_document_failed(document)
            return jsonify({"success": False, "error": str(exc)}), 400
        except ValueError as exc:
            logger.exception("Document processing failure")
            _mark_document_failed(document)
            return jsonify({"success": False, "error": str(exc)}), 400
        except Exception:
            logger.exception("Unexpected upload failure")
            _mark_document_failed(document)
            return jsonify(
                {"success": False, "error": "Failed to process the uploaded document."}
            ), 500

    @app.route("/api/documents/<int:document_id>", methods=["DELETE"])
    def delete_document(document_id: int):
        document = Document.query.get_or_404(document_id)

        try:
            delete_document_chunks(document.id)
        except EmbeddingServiceError as exc:
            logger.exception("Failed to delete document chunks")
            return jsonify({"success": False, "error": str(exc)}), 400

        db.session.delete(document)
        db.session.commit()

        return jsonify({"success": True})

    @app.route("/api/courses/<int:course_id>/ask", methods=["POST"])
    def ask_question(course_id: int):
        course = Course.query.get(course_id)
        if not course:
            return jsonify({"success": False, "error": "Course not found."}), 404

        payload = request.get_json(silent=True) or {}
        question = (payload.get("question") or "").strip()

        if not question:
            return jsonify({"success": False, "error": "Question cannot be empty."}), 400

        ready_count = Document.query.filter_by(course_id=course_id, status="ready").count()
        if ready_count == 0:
            return jsonify(
                {
                    "success": False,
                    "error": "Upload and process at least one document before asking questions.",
                }
            ), 400

        user_message = ChatMessage(
            course_id=course_id,
            role="user",
            content=question,
        )
        db.session.add(user_message)
        db.session.commit()

        try:
            result = answer_question(course_id, question)
        except TutorServiceError as exc:
            logger.exception("Tutor service failure")
            return jsonify({"success": False, "error": str(exc)}), 400
        except Exception:
            logger.exception("Unexpected tutor failure")
            return jsonify(
                {
                    "success": False,
                    "error": "Something went wrong while generating the answer.",
                }
            ), 500

        assistant_message = ChatMessage(
            course_id=course_id,
            role="assistant",
            content=result["answer"],
        )
        assistant_message.set_sources(result["sources"])
        db.session.add(assistant_message)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "answer": result["answer"],
                "sources": result["sources"],
            }
        )

    @app.route("/api/courses/<int:course_id>/clear-chat", methods=["POST"])
    def clear_chat(course_id: int):
        course = Course.query.get_or_404(course_id)
        ChatMessage.query.filter_by(course_id=course.id).delete()
        db.session.commit()
        return jsonify({"success": True})


def _mark_document_failed(document: Document) -> None:
    document.status = "failed"
    db.session.commit()


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "error": "Not found."}), 404

    @app.errorhandler(413)
    @app.errorhandler(RequestEntityTooLarge)
    def file_too_large(error):
        return jsonify({"success": False, "error": "File is too large. Maximum upload size is 4 MB."}), 413

    @app.errorhandler(500)
    def server_error(error):
        logger.exception("Internal server error")
        return jsonify({"success": False, "error": "Something went wrong. Please try again."}), 500


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
