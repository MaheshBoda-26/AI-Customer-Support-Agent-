"""
Standalone Knowledge Base Ingestion Script

This script can be run manually or via CI/CD to ingest documents into Qdrant.
Supports multiple file formats: .txt, .md, .pdf, .html, .json

Usage:
    python ingest_docs.py --source ./docs --recursive
    python ingest_docs.py --file ./docs/faq.md --title "FAQ"
    python ingest_docs.py --dir ./knowledge_base --pattern "*.md"
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Dict, Optional
import json

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.rag.chunker import chunk_text, DocumentChunk
from app.rag.embed import get_embedding_client
from app.core.config import settings

# Try to import unstructured for document parsing
try:
    from unstructured.partition.auto import partition
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    print("Warning: 'unstructured' not available. Only .txt and .md files supported.")

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance
except ImportError:
    print("Error: qdrant-client not installed. Run: pip install qdrant-client")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DocumentIngester:
    """Handles document loading, chunking, embedding, and upserting to Qdrant."""

    def __init__(self):
        self.embedding_client = get_embedding_client()
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
        )
        self.collection_name = "kb_chunks"
        self.vector_size = 1024  # voyage-3 dimension

    def ensure_collection(self):
        """Create Qdrant collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            logger.info(f"Creating collection '{self.collection_name}'")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )
        else:
            logger.info(f"Collection '{self.collection_name}' already exists")

    def load_text_file(self, file_path: Path) -> str:
        """Load text from a plain text or markdown file."""
        return file_path.read_text(encoding="utf-8")

    def load_document(self, file_path: Path) -> str:
        """Load document content based on file extension."""
        suffix = file_path.suffix.lower()

        if suffix in [".txt", ".md", ".markdown"]:
            return self.load_text_file(file_path)

        if not UNSTRUCTURED_AVAILABLE:
            raise ValueError(f"Cannot parse {suffix} files without 'unstructured' package")

        # Use unstructured for PDF, HTML, DOCX, etc.
        elements = partition(filename=str(file_path))
        return "\n\n".join([str(el) for el in elements])

    def process_file(
        self,
        file_path: Path,
        title: Optional[str] = None,
        section: Optional[str] = None,
        language: str = "en",
    ) -> List[DocumentChunk]:
        """Process a single file into chunks."""
        logger.info(f"Processing: {file_path}")

        try:
            content = self.load_document(file_path)
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            return []

        if not content.strip():
            logger.warning(f"Empty content in {file_path}")
            return []

        # Use filename as source if no title provided
        source = str(file_path.relative_to(Path.cwd())) if file_path.is_absolute() else str(file_path)
        doc_title = title or file_path.stem

        chunks = chunk_text(
            text=content,
            source=source,
            title=doc_title,
            section=section,
            language=language,
        )

        return chunks

    def process_directory(
        self,
        directory: Path,
        pattern: str = "*",
        recursive: bool = True,
        language: str = "en",
    ) -> List[DocumentChunk]:
        """Process all matching files in a directory."""
        all_chunks = []

        if recursive:
            files = directory.rglob(pattern)
        else:
            files = directory.glob(pattern)

        for file_path in files:
            if file_path.is_file():
                chunks = self.process_file(file_path, language=language)
                all_chunks.extend(chunks)

        return all_chunks

    def ingest_chunks(self, chunks: List[DocumentChunk], batch_size: int = 100):
        """Embed and upsert chunks to Qdrant in batches."""
        if not chunks:
            logger.warning("No chunks to ingest")
            return

        logger.info(f"Embedding and upserting {len(chunks)} chunks...")

        texts = [chunk.text for chunk in chunks]
        vectors = self.embedding_client.embed(texts)

        points = []
        for chunk, vector in zip(chunks, vectors):
            points.append(PointStruct(
                id=chunk.id,
                vector=vector,
                payload={
                    "text": chunk.text,
                    "source": chunk.source,
                    "doc_title": chunk.title,
                    "section": chunk.section,
                    "language": chunk.language,
                }
            ))

        # Batch upsert
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
            )
            logger.info(f"Upserted batch {i//batch_size + 1}/{(len(points)-1)//batch_size + 1}")

        logger.info(f"Successfully ingested {len(chunks)} chunks")


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into Qdrant knowledge base")
    parser.add_argument("--file", type=Path, help="Single file to ingest")
    parser.add_argument("--dir", type=Path, help="Directory to ingest")
    parser.add_argument("--pattern", default="*", help="File pattern (e.g., *.md)")
    parser.add_argument("--recursive", action="store_true", help="Recursively process subdirectories")
    parser.add_argument("--title", help="Document title (for single file)")
    parser.add_argument("--section", help="Document section (for single file)")
    parser.add_argument("--language", default="en", help="Document language code")
    parser.add_argument("--recreate", action="store_true", help="Recreate collection before ingesting")

    args = parser.parse_args()

    if not args.file and not args.dir:
        parser.error("Either --file or --dir is required")

    ingester = DocumentIngester()

    # Recreate collection if requested
    if args.recreate:
        logger.info(f"Deleting and recreating collection '{ingester.collection_name}'")
        try:
            ingester.client.delete_collection(ingester.collection_name)
        except Exception:
            pass
        ingester.ensure_collection()
    else:
        ingester.ensure_collection()

    all_chunks = []

    if args.file:
        chunks = ingester.process_file(
            args.file,
            title=args.title,
            section=args.section,
            language=args.language,
        )
        all_chunks.extend(chunks)

    if args.dir:
        chunks = ingester.process_directory(
            args.dir,
            pattern=args.pattern,
            recursive=args.recursive,
            language=args.language,
        )
        all_chunks.extend(chunks)

    if all_chunks:
        ingester.ingest_chunks(all_chunks)
        logger.info("Ingestion complete!")
    else:
        logger.warning("No content was ingested")


if __name__ == "__main__":
    main()