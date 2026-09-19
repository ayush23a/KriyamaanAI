import logging
from sentence_transformers import SentenceTransformer
from domain.ports.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


class SentenceTransformerEmbeddingAdapter(EmbeddingProvider):
    """Local Sentence Transformers embedding adapter implementing EmbeddingProvider."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        dimension: int = 384,
        device: str | None = None,
    ):
        self._model_name = model_name
        self._dimension = dimension
        self._device = device
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Loading SentenceTransformer model: %s", self._model_name)
            self._model = SentenceTransformer(self._model_name, device=self._device)
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return [arr.tolist() for arr in embeddings]

    def embed_query(self, text: str) -> list[float]:
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return embedding.tolist()

