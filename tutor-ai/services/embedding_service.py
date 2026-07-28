"""ChromaDB and OpenAI embedding operations."""

from __future__ import annotations

import logging
from typing import Any, Optional

import chromadb
from chromadb.config import Settings
from openai import OpenAI

from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DATA_DIR,
    EMBEDDING_MODEL,
    OPENAI_API_KEY,
)

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None
_chroma_client = None
_collection = None


class EmbeddingServiceError(Exception):
    """Raised when embedding or ChromaDB operations fail."""


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


def get_collection():
    """Return the persistent ChromaDB collection."""
    global _chroma_client, _collection

    if _collection is None:
        CHROMA_DATA_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_DATA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    return _collection


def build_chunk_id(course_id: int, document_id: int, chunk_index: int) -> str:
    """Create a unique chunk identifier."""
    return f"course_{course_id}_document_{document_id}_chunk_{chunk_index}"


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
    """Store document chunks and embeddings in ChromaDB."""
    if not chunks:
        return

    collection = get_collection()
    texts = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]
    ids = [
        build_chunk_id(
            chunk["metadata"]["course_id"],
            chunk["metadata"]["document_id"],
            chunk["metadata"]["chunk_index"],
        )
        for chunk in chunks
    ]

    try:
        embeddings = create_embeddings(texts)
        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
    except Exception as exc:
        logger.exception("Failed to add chunks to ChromaDB")
        raise EmbeddingServiceError(f"Failed to store document chunks: {exc}") from exc


def delete_document_chunks(document_id: int) -> None:
    """Delete all chunks belonging to a document."""
    collection = get_collection()
    try:
        collection.delete(where={"document_id": document_id})
    except Exception as exc:
        logger.exception("Failed to delete chunks for document %s", document_id)
        raise EmbeddingServiceError(
            f"Failed to delete document chunks: {exc}"
        ) from exc


def search_course_chunks(
    course_id: int, query_embedding: list[float], top_k: int = 5
) -> list[dict[str, Any]]:
    """Search ChromaDB for the most relevant chunks in a course."""
    collection = get_collection()

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"course_id": course_id},
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        logger.exception("ChromaDB search failed for course %s", course_id)
        raise EmbeddingServiceError(f"Failed to search course chunks: {exc}") from exc

    chunks = []
    if not results or not results.get("ids") or not results["ids"][0]:
        return chunks

    for idx, chunk_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][idx]
        document_text = results["documents"][0][idx]
        distance = results["distances"][0][idx] if results.get("distances") else None

        chunks.append(
            {
                "id": chunk_id,
                "text": document_text,
                "document_name": metadata.get("document_name", "Unknown"),
                "page_number": metadata.get("page_number", 0),
                "document_id": metadata.get("document_id"),
                "chunk_index": metadata.get("chunk_index"),
                "distance": distance,
            }
        )

    return chunks


def course_has_documents(course_id: int) -> bool:
    """Return True if the course has indexed chunks in ChromaDB."""
    collection = get_collection()
    try:
        results = collection.get(where={"course_id": course_id}, limit=1)
        return bool(results and results.get("ids"))
    except Exception as exc:
        logger.exception("Failed to check indexed documents for course %s", course_id)
        raise EmbeddingServiceError(
            f"Failed to check course documents: {exc}"
        ) from exc
