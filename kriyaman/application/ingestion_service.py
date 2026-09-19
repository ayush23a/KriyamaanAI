import hashlib
import uuid
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from domain.errors import ValidationError
from domain.models import Document as DomainDocument
from domain.ports.cache import CachePort
from domain.ports.embeddings import EmbeddingProvider
from persistence.models import DocumentChunkModel, DocumentModel
from persistence.repositories.chunk_repo import DocumentChunkRepository
from persistence.repositories.document_repo import DocumentRepository
from application.chunker import TextChunker
from application.parsers import DocumentParser, detect_mime_type, sanitize_filename

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit


class IngestionResult(BaseModel):
    document_id: str
    session_id: str
    name: str
    mime_type: str
    sha256: str
    chunks_count: int
    is_duplicate: bool
    status: str = "processed"


class IngestionService:
    """Orchestrates multi-format document ingestion, hashing, chunking, and embedding."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        chunker: TextChunker | None = None,
        cache_port: CachePort | None = None,
    ):
        self.embedding_provider = embedding_provider
        self.chunker = chunker or TextChunker()
        self.cache_port = cache_port

    async def ingest_document(
        self,
        session: AsyncSession,
        session_id: str,
        filename: str,
        content: bytes,
        extra_metadata: dict[str, Any] | None = None,
    ) -> IngestionResult:
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise ValidationError(
                f"File size ({len(content)} bytes) exceeds maximum limit of {MAX_FILE_SIZE_BYTES} bytes."
            )

        clean_filename = sanitize_filename(filename)
        mime_type = detect_mime_type(clean_filename, content)
        doc_hash = hashlib.sha256(content).hexdigest()

        doc_repo = DocumentRepository(session)
        chunk_repo = DocumentChunkRepository(session)

        # 1. Idempotency check: duplicate document in same session
        existing_doc = await doc_repo.get_by_session_and_hash(session_id, doc_hash)
        if existing_doc:
            existing_chunks = await chunk_repo.list_by_document(existing_doc.id)
            return IngestionResult(
                document_id=existing_doc.id,
                session_id=existing_doc.session_id,
                name=existing_doc.name,
                mime_type=existing_doc.mime_type,
                sha256=existing_doc.sha256,
                chunks_count=len(existing_chunks),
                is_duplicate=True,
                status=existing_doc.status,
            )

        # 2. Parse document text
        parsed_text, parse_metadata = DocumentParser.parse(clean_filename, content)
        combined_metadata = {**(extra_metadata or {}), **parse_metadata}

        # 3. Create document record
        document_id = str(uuid.uuid4())
        doc_model = await doc_repo.create(
            session_id=session_id,
            name=clean_filename,
            mime_type=mime_type,
            sha256=doc_hash,
            status="processing",
            metadata=combined_metadata,
            document_id=document_id,
        )

        # 4. Chunk document text
        domain_chunks = self.chunker.chunk_text(
            document_id=document_id,
            text=parsed_text,
            base_metadata={"session_id": session_id, "document_name": clean_filename},
        )

        if not domain_chunks:
            doc_model.status = "failed"
            await session.flush()
            raise ValidationError("Document produced 0 text chunks.")

        # 5. Compute embeddings in batch
        chunk_texts = [chunk.content for chunk in domain_chunks]
        embeddings = self.embedding_provider.embed_documents(chunk_texts)

        # 6. Create chunk models
        chunk_models: list[DocumentChunkModel] = []
        for chunk, embedding in zip(domain_chunks, embeddings):
            model = DocumentChunkModel(
                id=chunk.id,
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                content_hash=chunk.content_hash,
                embedding=embedding,
                metadata_json=chunk.metadata,
            )
            chunk_models.append(model)

        await chunk_repo.create_batch(chunk_models)

        # 7. Transition status to processed
        doc_model.status = "processed"
        await session.flush()

        # 8. Invalidate retrieval cache for session if cache available
        if self.cache_port:
            self.cache_port.delete_namespace(f"retrieval:{session_id}")

        return IngestionResult(
            document_id=document_id,
            session_id=session_id,
            name=clean_filename,
            mime_type=mime_type,
            sha256=doc_hash,
            chunks_count=len(chunk_models),
            is_duplicate=False,
            status="processed",
        )

