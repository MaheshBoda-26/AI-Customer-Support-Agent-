"""
Text chunking utilities for document ingestion.
"""
import logging
from typing import List
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Represents a chunk of a document with metadata."""
    id: str
    text: str
    source: str
    title: Optional[str] = None
    section: Optional[str] = None
    language: str = "en"


def chunk_text(
    text: str,
    source: str,
    title: Optional[str] = None,
    section: Optional[str] = None,
    language: str = "en",
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[DocumentChunk]:
    """
    Split text into overlapping chunks using RecursiveCharacterTextSplitter.

    Args:
        text: The text to chunk
        source: Source identifier (filename, URL, etc.)
        title: Optional document title
        section: Optional section within document
        language: Document language code
        chunk_size: Target chunk size in tokens (approximate)
        chunk_overlap: Overlap between chunks in tokens

    Returns:
        List of DocumentChunk objects
    """
    if not text or not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_text(text)

    document_chunks = []
    for i, chunk in enumerate(chunks):
        if chunk.strip():
            chunk_id = f"{source}-{i}"
            document_chunks.append(DocumentChunk(
                id=chunk_id,
                text=chunk.strip(),
                source=source,
                title=title,
                section=section,
                language=language,
            ))

    logger.info(f"Chunked document '{source}' into {len(document_chunks)} chunks")
    return document_chunks


def chunk_documents(
    documents: List[dict],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[DocumentChunk]:
    """
    Chunk multiple documents.

    Args:
        documents: List of dicts with keys: text, source, title (optional), section (optional), language (optional)
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks

    Returns:
        List of all DocumentChunk objects
    """
    all_chunks = []
    for doc in documents:
        chunks = chunk_text(
            text=doc.get("text", ""),
            source=doc.get("source", "unknown"),
            title=doc.get("title"),
            section=doc.get("section"),
            language=doc.get("language", "en"),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        all_chunks.extend(chunks)
    return all_chunks