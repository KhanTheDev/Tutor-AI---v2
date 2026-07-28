"""OpenAI embedding generation and pgvector storage/search."""

from __future__ import annotations

import logging
from typing import Any, Optional

from openai import OpenAI

from config import EMBEDDING_MODEL, OPENAI_API_KEY
from models import Chunk, db

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None


class EmbeddingServiceError(Exception):
    """Raised when embedding generation or chunk storage/search fails."""


def get_openai_client() -> OpenAI:
    """Return a configured OpenAI client."""
    global _client
    if not OPENAI_API_KEY:
        raise EmbeddingServiceError(
            "OPENAI_API_KEY is not configured. Add it to your .env file."
        )
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def create_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts."""
    if not texts:
        return []

    try:
        client = get_openai_client()
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in response.data]
    except Exception as exc:
        logger.exception("OpenAI embedding generation failed")
        raise EmbeddingServiceError(f"Failed to generate embeddings: {exc}") from exc


def create_query_embedding(text: str) -> list[float]:
    """Generate an embedding for a single query string."""
    embeddings = create_embeddings([text])
    return embeddings[0]


def add_document_chunks(chunks: list[dict]) -> None:
    """Embed and store document chunks in Postgres."""
    if not chunks:
        return

    try:
        texts = [chunk["text"] for chunk in chunks]
        embeddings = create_embeddings(texts)

        rows = [
            Chunk(
                course_id=chunk["metadata"]["course_id"],
                document_id=chunk["metadata"]["document_id"],
                document_name=chunk["metadata"]["document_name"],
                page_number=chunk["metadata"]["page_number"],
                chunk_index=chunk["metadata"]["chunk_index"],
                text=chunk["text"],
                embedding=embedding,
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        db.session.add_all(rows)
        db.session.commit()
    except EmbeddingServiceError:
        raise
    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to store document chunks")
        raise EmbeddingServiceError(f"Failed to store document chunks: {exc}") from exc


def delete_document_chunks(document_id: int) -> None:
    """Delete all chunks belonging to a document."""
    try:
        Chunk.query.filter_by(document_id=document_id).delete()
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to delete chunks for document %s", document_id)
        raise EmbeddingServiceError(
            f"Failed to delete document chunks: {exc}"
        ) from exc


def search_course_chunks(
    course_id: int, query_embedding: list[float], top_k: int = 5
) -> list[dict[str, Any]]:
    """Search Postgres/pgvector for the most relevant chunks in a course."""
    try:
        results = (
            Chunk.query.filter_by(course_id=course_id)
            .order_by(Chunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
            .all()
        )
    except Exception as exc:
        logger.exception("Chunk search failed for course %s", course_id)
        raise EmbeddingServiceError(f"Failed to search course chunks: {exc}") from exc

    return [
        {
            "id": chunk.id,
            "text": chunk.text,
            "document_name": chunk.document_name,
            "page_number": chunk.page_number,
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
        }
        for chunk in results
    ]


def course_has_documents(course_id: int) -> bool:
    """Return True if the course has indexed chunks."""
    try:
        return (
            db.session.query(Chunk.id).filter_by(course_id=course_id).first()
            is not None
        )
    except Exception as exc:
        logger.exception("Failed to check indexed documents for course %s", course_id)
        raise EmbeddingServiceError(
            f"Failed to check course documents: {exc}"
        ) from exc
