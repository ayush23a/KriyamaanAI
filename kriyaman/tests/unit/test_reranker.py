from datetime import datetime, timezone
from domain.models import EvidenceItem
from adapters.reranking.baseline import DeterministicReranker


def test_deterministic_reranker_scoring():
    reranker = DeterministicReranker(vector_weight=0.5, lexical_weight=0.5)

    item1 = EvidenceItem(
        evidence_id="ev_1",
        source_type="document",
        source_id="doc_1",
        title="Doc 1",
        content="This article discusses planetary astrophysics and distant galaxies.",
        retrieval_method="vector",
        retrieval_score=0.8,
        retrieved_at=datetime.now(timezone.utc),
    )

    item2 = EvidenceItem(
        evidence_id="ev_2",
        source_type="document",
        source_id="doc_2",
        title="Doc 2",
        content="Refund policy: Customers can request a full refund within 30 days of purchase.",
        retrieval_method="vector",
        retrieval_score=0.75,
        retrieved_at=datetime.now(timezone.utc),
    )

    query = "How do I request a full refund?"
    ranked = reranker.rerank(query, [item1, item2], top_k=2)

    assert len(ranked) == 2
    # item2 has lexical overlap with 'refund' and 'full', so it should rank first
    assert ranked[0].evidence_id == "ev_2"
    assert ranked[0].rerank_score is not None
    assert ranked[0].rerank_score > ranked[1].rerank_score


def test_deterministic_reranker_top_k():
    reranker = DeterministicReranker()
    items = [
        EvidenceItem(
            evidence_id=f"ev_{i}",
            source_type="document",
            source_id=f"doc_{i}",
            content=f"Content {i}",
            retrieval_method="vector",
            retrieval_score=0.5,
            retrieved_at=datetime.now(timezone.utc),
        )
        for i in range(10)
    ]

    ranked = reranker.rerank("query", items, top_k=3)
    assert len(ranked) == 3


def test_deterministic_reranker_empty():
    reranker = DeterministicReranker()
    assert reranker.rerank("query", [], top_k=5) == []

