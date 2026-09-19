from domain.ports.embeddings import EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic fake embedding provider generating fixed-dimension vectors."""

    def __init__(self, dim: int = 384):
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text) % 10) / 10.0] * self._dim for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1] * self._dim

