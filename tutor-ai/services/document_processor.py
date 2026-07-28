"""Document extraction, cleaning, and chunking utilities.

Files are processed entirely in memory — nothing is written to disk. This
keeps the app compatible with read-only serverless filesystems (Vercel), and
there's no need to persist the original file since only its extracted text
is ever used.
"""

import base64
import logging
import re

import fitz
from openai import OpenAI

from config import CHUNK_OVERLAP, CHUNK_SIZE, OPENAI_API_KEY, VISION_MODEL

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"pdf", "txt", "jpg", "jpeg", "png"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}

VISION_PROMPT = (
    "Transcribe all text visible in this image exactly as written, including "
    "handwritten notes. Preserve the original structure (headings, lists, "
    "diagrams described in words). Do not summarize, translate, or add "
    "commentary — output only the transcribed text."
)


def allowed_file(filename: str) -> bool:
    """Return True if the filename has an allowed extension."""
    if not filename or "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def get_file_type(filename: str) -> str:
    """Return the lowercase file extension."""
    return filename.rsplit(".", 1)[1].lower()


def clean_text(text: str) -> str:
    """Normalize whitespace and remove control characters."""
    if not text:
        return ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_text(file_bytes: bytes) -> list[dict]:
    """Extract text from each PDF page with metadata."""
    pages = []

    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page_index in range(len(doc)):
                page = doc[page_index]
                text = clean_text(page.get_text("text"))
                if text:
                    pages.append(
                        {
                            "text": text,
                            "page_number": page_index + 1,
                        }
                    )
    except Exception as exc:
        logger.exception("Failed to extract PDF text")
        raise ValueError(f"Could not extract text from PDF: {exc}") from exc

    return pages


def extract_txt_text(file_bytes: bytes) -> list[dict]:
    """Extract text from a TXT file as a single page."""
    try:
        raw_text = file_bytes.decode("utf-8", errors="ignore")
    except Exception as exc:
        logger.exception("Failed to read TXT file")
        raise ValueError(f"Could not read text file: {exc}") from exc

    text = clean_text(raw_text)
    if not text:
        return []

    return [{"text": text, "page_number": 1}]


def extract_image_text(file_bytes: bytes, file_type: str) -> list[dict]:
    """Transcribe text from an image using a vision-capable model."""
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY is not configured. Add it to your .env file."
        )

    media_type = "jpeg" if file_type == "jpg" else file_type

    try:
        image_data = base64.b64encode(file_bytes).decode("utf-8")
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{media_type};base64,{image_data}"
                            },
                        },
                    ],
                }
            ],
        )
        raw_text = response.choices[0].message.content or ""
    except Exception as exc:
        logger.exception("Failed to transcribe image")
        raise ValueError(f"Could not transcribe image: {exc}") from exc

    text = clean_text(raw_text)
    if not text:
        return []

    return [{"text": text, "page_number": 1}]


def split_text_into_chunks(
    text: str,
    course_id: int,
    document_id: int,
    document_name: str,
    page_number: int,
    start_chunk_index: int = 0,
) -> list[dict]:
    """Split page text into overlapping chunks without cutting words when possible."""
    chunks = []
    if not text:
        return chunks

    text_length = len(text)
    start = 0
    chunk_index = start_chunk_index

    while start < text_length:
        end = min(start + CHUNK_SIZE, text_length)

        if end < text_length:
            split_at = text.rfind(" ", start, end)
            if split_at == -1 or split_at <= start:
                split_at = end
            end = split_at

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": {
                        "course_id": course_id,
                        "document_id": document_id,
                        "document_name": document_name,
                        "page_number": page_number,
                        "chunk_index": chunk_index,
                    },
                }
            )
            chunk_index += 1

        if end >= text_length:
            break

        next_start = end - CHUNK_OVERLAP
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks


def process_document_file(
    file_bytes: bytes,
    file_type: str,
    course_id: int,
    document_id: int,
    document_name: str,
) -> tuple[list[dict], int]:
    """
    Extract text from a document and return chunks plus total page count.

    Returns:
        (chunks, total_pages)
    """
    file_type = file_type.lower()

    if file_type == "pdf":
        pages = extract_pdf_text(file_bytes)
    elif file_type == "txt":
        pages = extract_txt_text(file_bytes)
    elif file_type in IMAGE_EXTENSIONS:
        pages = extract_image_text(file_bytes, file_type)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    if not pages:
        raise ValueError("The uploaded document contains no extractable text.")

    all_chunks = []
    chunk_index = 0

    for page in pages:
        page_chunks = split_text_into_chunks(
            text=page["text"],
            course_id=course_id,
            document_id=document_id,
            document_name=document_name,
            page_number=page["page_number"],
            start_chunk_index=chunk_index,
        )
        all_chunks.extend(page_chunks)
        if page_chunks:
            chunk_index = page_chunks[-1]["metadata"]["chunk_index"] + 1

    total_pages = len(pages)
    return all_chunks, total_pages
