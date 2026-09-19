import hashlib
import uuid
from domain.models import DocumentChunk


class TextChunker:
    """Deterministic chunker splitting text into overlapping chunks with content hashing."""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(
        self,
        document_id: str,
        text: str,
        base_metadata: dict | None = None,
    ) -> list[DocumentChunk]:
        if not text.strip():
            return []

        chunks: list[DocumentChunk] = []
        start = 0
        text_len = len(text)
        chunk_index = 0

        while start < text_len:
            end = start + self.chunk_size

            if end < text_len:
                # Look for natural split point within overlap window
                split_candidates = ["\n\n", "\n", ". ", " "]
                found_split = False
                search_region = text[max(start, end - self.chunk_overlap) : end]

                for sep in split_candidates:
                    pos = search_region.rfind(sep)
                    if pos != -1:
                        end = max(start, end - self.chunk_overlap) + pos + len(sep)
                        found_split = True
                        break

            chunk_content = text[start:end].strip()
            if chunk_content:
                content_hash = hashlib.sha256(chunk_content.encode("utf-8")).hexdigest()
                metadata = dict(base_metadata or {})
                metadata.update({
                    "start_char": start,
                    "end_char": end,
                    "char_count": len(chunk_content),
                })

                chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    chunk_index=chunk_index,
                    content=chunk_content,
                    content_hash=content_hash,
                    metadata=metadata,
                )
                chunks.append(chunk)
                chunk_index += 1

            # Advance window
            if end >= text_len:
                break
            start = max(start + 1, end - self.chunk_overlap)

        return chunks

