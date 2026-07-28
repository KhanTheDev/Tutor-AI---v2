"""Tutor AI Platform - Flask application entry point."""

import logging

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
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

    db.init_app(app)

    with app.app_context():
        db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.session.commit()
        db.create_all()

    register_routes(app)
    register_error_handlers(app)

    return app


def register_routes(app: Flask) -> None:
    @app.route("/")
    def index():
        courses = Course.query.order_by(Course.created_at.desc()).all()
        return render_template("index.html", courses=courses)

    @app.route("/courses/<int:course_id>")
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
        return render_template(
            "course.html",
            course=course,
            documents=documents,
            messages=messages,
        )

    @app.route("/courses/<int:course_id>/upload", methods=["POST"])
    def upload_document(course_id: int):
        course = Course.query.get_or_404(course_id)

        if "document" not in request.files:
            flash("No file was selected.", "danger")
            return redirect(url_for("course_detail", course_id=course_id))

        file = request.files["document"]
        if not file or not file.filename:
            flash("No file was selected.", "danger")
            return redirect(url_for("course_detail", course_id=course_id))

        original_filename = file.filename
        if not allowed_file(original_filename):
            flash("Only PDF, TXT, JPG, and PNG files are supported.", "danger")
            return redirect(url_for("course_detail", course_id=course_id))

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

            flash(
                f'"{original_filename}" uploaded and processed successfully '
                f"({len(chunks)} chunks).",
                "success",
            )
        except EmbeddingServiceError as exc:
            logger.exception("Embedding failure during upload")
            _mark_document_failed(document)
            flash(str(exc), "danger")
        except ValueError as exc:
            logger.exception("Document processing failure")
            _mark_document_failed(document)
            flash(str(exc), "danger")
        except Exception:
            logger.exception("Unexpected upload failure")
            _mark_document_failed(document)
            flash("Failed to process the uploaded document.", "danger")

        return redirect(url_for("course_detail", course_id=course_id))

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

    @app.route("/courses/<int:course_id>/clear-chat", methods=["POST"])
    def clear_chat(course_id: int):
        course = Course.query.get_or_404(course_id)
        ChatMessage.query.filter_by(course_id=course.id).delete()
        db.session.commit()
        flash("Chat history cleared.", "success")
        return redirect(url_for("course_detail", course_id=course_id))

    @app.route("/documents/<int:document_id>/delete", methods=["POST"])
    def delete_document(document_id: int):
        document = Document.query.get_or_404(document_id)
        course_id = document.course_id

        try:
            delete_document_chunks(document.id)
        except EmbeddingServiceError as exc:
            logger.exception("Failed to delete document chunks")
            flash(str(exc), "danger")
            return redirect(url_for("course_detail", course_id=course_id))

        db.session.delete(document)
        db.session.commit()

        flash(f'"{document.original_filename}" deleted successfully.', "success")
        return redirect(url_for("course_detail", course_id=course_id))

    @app.route("/courses/<int:course_id>/delete", methods=["POST"])
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

        flash(f'Course "{course.name}" deleted successfully.', "success")
        return redirect(url_for("index"))


def _mark_document_failed(document: Document) -> None:
    document.status = "failed"
    db.session.commit()


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", title="Not Found", message="Page not found."), 404

    @app.errorhandler(413)
    @app.errorhandler(RequestEntityTooLarge)
    def file_too_large(error):
        flash("File is too large. Maximum upload size is 25 MB.", "danger")
        return redirect(request.referrer or url_for("index"))

    @app.errorhandler(500)
    def server_error(error):
        logger.exception("Internal server error")
        return render_template(
            "error.html",
            title="Server Error",
            message="Something went wrong. Please try again.",
        ), 500


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
