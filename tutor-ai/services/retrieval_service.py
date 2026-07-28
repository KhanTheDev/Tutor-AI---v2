"""Retrieve relevant course chunks for a student question."""

import logging
from typing import Any

from config import RETRIEVAL_TOP_K
from services.embedding_service import (
    EmbeddingServiceError,
    create_query_embedding,
    search_course_chunks,
)

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def deduplicate_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate or nearly identical retrieved chunks."""
    unique_chunks = []
    seen_keys = set()

    for chunk in chunks:
        key = (
            chunk.get("document_name"),
            chunk.get("page_number"),
            _normalize_text(chunk.get("text", ""))[:200],
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_chunks.append(chunk)

    return unique_chunks


def retrieve_relevant_chunks(course_id: int, question: str) -> list[dict[str, Any]]:
    """
    Embed the question and retrieve the most relevant course chunks.

    Returns an empty list when no useful chunks are found.
    """
    question = question.strip()
    if not question:
        return []

    try:
        query_embedding = create_query_embedding(question)
        chunks = search_course_chunks(
            course_id=course_id,
            query_embedding=query_embedding,
            top_k=RETRIEVAL_TOP_K,
        )
        return deduplicate_chunks(chunks)
    except EmbeddingServiceError:
        raise
    except Exception as exc:
        logger.exception("Retrieval failed for course %s", course_id)
        raise EmbeddingServiceError(f"Retrieval failed: {exc}") from exc
