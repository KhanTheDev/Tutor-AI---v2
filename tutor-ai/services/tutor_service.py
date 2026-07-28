"""Generate tutor answers using retrieved course materials."""

import logging
from typing import Any

from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL
from services.embedding_service import EmbeddingServiceError, course_has_documents
from services.retrieval_service import retrieve_relevant_chunks

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful AI tutor.

Answer the student's question using only the provided course materials.

Do not use outside knowledge.

If the answer cannot be found in the provided course materials, clearly say:

"I could not find enough information in the uploaded course materials to answer this question."

Explain the answer clearly and in student-friendly language.

When appropriate, provide examples or step-by-step explanations.

Do not make up facts, citations, page numbers, definitions, formulas, or quotes."""

FALLBACK_ANSWER = (
    "I could not find enough information in the uploaded course materials "
    "to answer this question."
)


class TutorServiceError(Exception):
    """Raised when tutor answer generation fails."""


def get_groq_client() -> Groq:
    if not GROQ_API_KEY:
        raise TutorServiceError(
            "GROQ_API_KEY is not configured. Add it to your .env file."
        )
    return Groq(api_key=GROQ_API_KEY)


def build_source_list(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build a deduplicated list of source references."""
    sources = []
    seen = set()

    for chunk in chunks:
        key = (chunk.get("document_name"), chunk.get("page_number"))
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "document_name": chunk.get("document_name", "Unknown"),
                "page_number": chunk.get("page_number", 0),
            }
        )

    return sources


def build_context_prompt(chunks: list[dict[str, Any]]) -> str:
    """Format retrieved chunks for the language model prompt."""
    if not chunks:
        return "No course materials were retrieved."

    sections = []
    for index, chunk in enumerate(chunks, start=1):
        sections.append(
            "\n".join(
                [
                    f"SOURCE {index}",
                    f"Document: {chunk.get('document_name', 'Unknown')}",
                    f"Page: {chunk.get('page_number', 'Unknown')}",
                    "Content:",
                    chunk.get("text", ""),
                ]
            )
        )

    return "\n\n".join(sections)


def answer_question(course_id: int, question: str) -> dict[str, Any]:
    """
    Retrieve relevant chunks and generate a grounded tutor answer.

    Returns:
        {
            "answer": str,
            "sources": [{"document_name": str, "page_number": int}, ...]
        }
    """
    question = question.strip()
    if not question:
        raise TutorServiceError("Question cannot be empty.")

    if not course_has_documents(course_id):
        raise TutorServiceError(
            "This course has no processed documents yet. Upload materials first."
        )

    try:
        chunks = retrieve_relevant_chunks(course_id, question)
    except EmbeddingServiceError as exc:
        raise TutorServiceError(str(exc)) from exc

    sources = build_source_list(chunks)

    if not chunks:
        return {"answer": FALLBACK_ANSWER, "sources": []}

    user_prompt = (
        "Use only the following course materials to answer the student's question.\n\n"
        f"{build_context_prompt(chunks)}\n\n"
        f"Student question:\n{question}"
    )

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        answer = (response.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.exception("Groq chat completion failed")
        raise TutorServiceError(
            "The AI tutor is temporarily unavailable. Please try again."
        ) from exc

    if not answer:
        answer = FALLBACK_ANSWER

    return {"answer": answer, "sources": sources}
