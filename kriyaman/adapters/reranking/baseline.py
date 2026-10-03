import re
from domain.models import EvidenceItem
from domain.ports.reranker import Reranker
from application.evidence_judge import STOPWORDS


class DeterministicReranker(Reranker):
    """Deterministic local reranker combining vector score and lexical overlap."""

    def __init__(self, vector_weight: float = 0.6, lexical_weight: float = 0.4):
        self.vector_weight = vector_weight
        self.lexical_weight = lexical_weight

    def _tokenize(self, text: str) -> set[str]:
        clean = re.findall(r"[a-zA-Z0-9]{2,}", text.lower().replace("_", " ").replace("-", " "))
        sub = re.findall(r"[a-zA-Z]{2,}|[0-9]+", text.lower())
        return set(clean) | set(sub)

    def rerank(self, query: str, items: list[EvidenceItem], top_k: int) -> list[EvidenceItem]:
        if not items:
            return []

        query_tokens = self._tokenize(query)
        content_query_tokens = {w for w in query_tokens if w not in STOPWORDS}
        eval_query_tokens = content_query_tokens if content_query_tokens else query_tokens

        scored_items: list[tuple[float, EvidenceItem]] = []

        for item in items:
            vector_score = item.retrieval_score if item.retrieval_score is not None else 0.5

            content_tokens = self._tokenize(item.content)
            if eval_query_tokens:
                overlap = len(eval_query_tokens & content_tokens)
                lexical_score = overlap / len(eval_query_tokens)
            else:
                lexical_score = 0.0

            # Exact phrase bonus
            if query.lower() in item.content.lower():
                lexical_score = min(1.0, lexical_score + 0.3)

            combined_score = (self.vector_weight * vector_score) + (self.lexical_weight * lexical_score)
            combined_score = round(min(1.0, max(0.0, combined_score)), 4)

            # Return updated copy with both rerank_score and updated retrieval_score
            updated_item = item.model_copy(
                update={
                    "rerank_score": combined_score,
                    "retrieval_score": max(vector_score, combined_score),
                }
            )
            scored_items.append((combined_score, updated_item))

        scored_items.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored_items[:top_k]]


DeterministicBaselineReranker = DeterministicReranker


