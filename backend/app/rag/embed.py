"""
Embedding client wrapper for Voyage AI or OpenAI.
"""
import logging
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """Wrapper for embedding providers."""

    def __init__(self):
        self.model = settings.EMBEDDING_MODEL
        self._voyage_client = None
        self._openai_client = None

        if self.model.startswith("voyage"):
            try:
                import voyageai
                self._voyage_client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
            except ImportError:
                logger.warning("voyageai package not installed")
        elif self.model.startswith("text-embedding"):
            try:
                from openai import OpenAI
                self._openai_client = OpenAI()
            except ImportError:
                logger.warning("openai package not installed")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts."""
        if not texts:
            return []

        if self.model.startswith("voyage") and self._voyage_client:
            return self._embed_voyage(texts)
        elif self.model.startswith("text-embedding") and self._openai_client:
            return self._embed_openai(texts)
        else:
            raise ValueError(f"Unsupported embedding model: {self.model}")

    def embed_single(self, text: str) -> List[float]:
        """Embed a single text."""
        return self.embed([text])[0]

    def _embed_voyage(self, texts: List[str]) -> List[List[float]]:
        """Embed using Voyage AI."""
        result = self._voyage_client.embed(texts, model=self.model, input_type="document")
        return result.embeddings

    def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        """Embed using OpenAI."""
        result = self._openai_client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in result.data]


# Singleton instance
_embedding_client: Optional[EmbeddingClient] = None


def get_embedding_client() -> EmbeddingClient:
    """Get or create the singleton embedding client."""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client