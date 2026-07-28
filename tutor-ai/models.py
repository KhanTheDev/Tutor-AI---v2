import json
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    documents = db.relationship(
        "Document", back_populates="course", cascade="all, delete-orphan"
    )
    chat_messages = db.relationship(
        "ChatMessage", back_populates="course", cascade="all, delete-orphan"
    )

    @property
    def document_count(self):
        return len(self.documents)

    @property
    def ready_document_count(self):
        return sum(1 for doc in self.documents if doc.status == "ready")


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    saved_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    upload_date = db.Column(db.DateTime, default=utcnow, nullable=False)
    status = db.Column(db.String(20), default="uploaded", nullable=False)
    total_pages = db.Column(db.Integer, default=0, nullable=False)
    total_chunks = db.Column(db.Integer, default=0, nullable=False)

    course = db.relationship("Course", back_populates="documents")


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sources = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    course = db.relationship("Course", back_populates="chat_messages")

    def get_sources(self):
        if not self.sources:
            return []
        try:
            return json.loads(self.sources)
        except json.JSONDecodeError:
            return []

    def set_sources(self, sources_list):
        self.sources = json.dumps(sources_list)
