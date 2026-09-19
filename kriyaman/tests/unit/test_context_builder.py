from domain.models import EvidenceAssessment, EvidenceItem, MemoryItem
from application.context_builder import ContextBuilder


def test_context_builder_basic():
    builder = ContextBuilder()
    evidence = [
        EvidenceItem(
            evidence_id="ev_1",
            source_type="document",
            source_id="d1",
            content="Returns accepted within 30 days.",
            retrieval_method="vector",
            retrieval_score=0.9,
        )
    ]
    memories = [
        MemoryItem(
            id="m1",
            memory_principal_id="p1",
            content="User prefers concise answers.",
        )
    ]

    pkg = builder.build_context(
        query="What is the return window?",
        evidence=evidence,
        memory_items=memories,
    )

    assert pkg.normalized_query == "What is the return window?"
    assert len(pkg.evidence_items) == 1
    assert pkg.evidence_items[0].evidence_id == "ev_1"
    assert len(pkg.memory_items) == 1
    assert pkg.conflict_instructions is None
    assert pkg.total_tokens > 0


def test_context_builder_conflict_instructions():
    builder = ContextBuilder()
    assessment = EvidenceAssessment(
        decision="conflicting",
        coverage_score=0.7,
        quality_score=0.7,
        confidence=0.8,
        conflict_groups=[["ev_1", "ev_2"]],
        reason_code="conflict",
    )

    pkg = builder.build_context(
        query="is return free",
        evidence=[],
        assessment=assessment,
    )

    assert pkg.conflict_instructions is not None
    assert "Contradictory evidence" in pkg.conflict_instructions


def test_context_builder_token_budget_trimming():
    builder = ContextBuilder(chars_per_token=4)
    # Create 5 items with varying scores
    evidence = [
        EvidenceItem(
            evidence_id=f"ev_{i}",
            source_type="document",
            source_id=f"d_{i}",
            content=f"Long document chunk text for evidence item number {i} " * 5,
            retrieval_method="vector",
            retrieval_score=0.5 + (i * 0.1),
        )
        for i in range(5)
    ]

    # Set tight budget (e.g. 350 tokens ~ 1400 chars)
    pkg = builder.build_context(
        query="test query",
        evidence=evidence,
        max_tokens=350,
    )

    # Some evidence must be trimmed due to budget
    assert 0 < len(pkg.evidence_items) < len(evidence)
    # Highest scoring items should be retained first (ev_4 has score 0.9)
    assert pkg.evidence_items[0].evidence_id == "ev_4"
