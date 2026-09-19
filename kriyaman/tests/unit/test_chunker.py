import pytest
from application.chunker import TextChunker


def test_chunker_basic():
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    text = "Paragraph one with some detailed words.\n\nParagraph two with additional explanation and sentences."
    chunks = chunker.chunk_text(document_id="doc_1", text=text)

    assert len(chunks) >= 1
    assert chunks[0].document_id == "doc_1"
    assert chunks[0].chunk_index == 0
    assert chunks[0].content_hash is not None
    assert len(chunks[0].content_hash) == 64  # SHA-256


def test_chunker_deterministic():
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    text = "Deterministic testing text that will be split across multiple chunks evenly."
    chunks1 = chunker.chunk_text("doc_1", text)
    chunks2 = chunker.chunk_text("doc_1", text)

    assert len(chunks1) == len(chunks2)
    for c1, c2 in zip(chunks1, chunks2):
        assert c1.content == c2.content
        assert c1.content_hash == c2.content_hash
        assert c1.chunk_index == c2.chunk_index


def test_chunker_invalid_overlap():
    with pytest.raises(ValueError):
        TextChunker(chunk_size=100, chunk_overlap=100)


def test_chunker_empty_text():
    chunker = TextChunker()
    chunks = chunker.chunk_text("doc_1", "   \n   ")
    assert chunks == []

