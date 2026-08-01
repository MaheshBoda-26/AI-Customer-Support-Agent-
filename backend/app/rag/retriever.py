"""
Qdrant retriever for vector similarity search.
"""
import logging
from typing import List, Optional
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.config import settings
from app.rag.embed import get_embedding_client

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A retrieved chunk with metadata and score."""
    text: str
    source: str
    title: Optional[str] = None
    section: Optional[str] = None
    language: Optional[str] = None
    score: float = 0.0


class QdrantRetriever:
    """Qdrant vector search retriever."""

    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
        )
        self.collection_name = "kb_chunks"
        self.embedding_client = get_embedding_client()

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        language: Optional[str] = None,
        score_threshold: float = 0.5,
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: Search query text
            top_k: Number of results to return (default from settings)
            language: Optional language filter
            score_threshold: Minimum similarity score

        Returns:
            List of RetrievedChunk objects sorted by score
        """
        if top_k is None:
            top_k = settings.DEFAULT_TOP_K

        # Embed the query
        query_vector = self.embedding_client.embed_single(query)

        # Build filter if language specified
        query_filter = None
        if language:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="language",
                        match=MatchValue(value=language),
                    )
                ]
            )

        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )

        chunks = []
        for hit in results:
            payload = hit.payload or {}
            chunks.append(RetrievedChunk(
                text=payload.get("text", ""),
                source=payload.get("source", ""),
                title=payload.get("doc_title"),
                section=payload.get("section"),
                language=payload.get("language"),
                score=hit.score,
            ))

        logger.info(f"Retrieved {len(chunks)} chunks for query: {query[:50]}...")
        return chunks

    def health_check(self) -> bool:
        """Check if Qdrant is accessible."""
        try:
            collections = self.client.get_collections()
            return any(c.name == self.collection_name for c in collections.collections)
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False


# Singleton instance
_retriever: Optional[QdrantRetriever] = None


def get_retriever() -> QdrantRetriever:
    """Get or create the singleton retriever."""
    global _retriever
    if _retriever is None:
        _retriever = QdrantRetriever()
    return _retriever