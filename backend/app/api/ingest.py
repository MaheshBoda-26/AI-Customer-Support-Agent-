"""
Ingest API endpoint for knowledge base updates.
"""
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List

from app.rag.chunker import chunk_text, DocumentChunk
from app.rag.embed import get_embedding_client
from app.db.models import IngestRequest
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest")
async def ingest_endpoint(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
):
    """
    Ingest a document into the knowledge base.
    Chunks, embeds, and upserts to Qdrant.
    """
    logger.info(f"Ingest request: source={request.source}, title={request.title}")

    try:
        # Chunk the document
        chunks = chunk_text(
            text=request.content,
            source=request.source,
            title=request.title,
            section=request.section,
            language=request.language,
        )

        if not chunks:
            raise HTTPException(status_code=400, detail="No content to ingest")

        # Embed chunks
        embedding_client = get_embedding_client()
        texts = [chunk.text for chunk in chunks]
        vectors = embedding_client.embed(texts)

        # Upsert to Qdrant
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct

        client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
        )

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
        client.upsert(
            collection_name="kb_chunks",
            points=points,
        )

        logger.info(f"Successfully ingested {len(chunks)} chunks from {request.source}")

        return {
            "status": "success",
            "chunks_ingested": len(chunks),
            "source": request.source,
        }

    except Exception as e:
        logger.error(f"Ingest failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/ingest/batch")
async def ingest_batch_endpoint(
    requests: List[IngestRequest],
    background_tasks: BackgroundTasks,
):
    """Ingest multiple documents in batch."""
    results = []
    for req in requests:
        try:
            result = await ingest_endpoint(req, background_tasks)
            results.append(result)
        except Exception as e:
            results.append({
                "status": "error",
                "source": req.source,
                "error": str(e),
            })

    return {"results": results}