from domain.models import AcquisitionPlan, EvidenceItem
from application.evidence_judge import EvidenceJudge


def test_judge_no_acquisition_plan():
    judge = EvidenceJudge()
    plan = AcquisitionPlan(action="no_acquisition_required", reason_code="greeting")
    assessment = judge.evaluate(query="hello", evidence=[], current_plan=plan)

    assert assessment.decision == "sufficient"
    assert assessment.coverage_score == 1.0
    assert assessment.confidence == 1.0


def test_judge_clarification_plan():
    judge = EvidenceJudge()
    plan = AcquisitionPlan(action="clarify", reason_code="ambiguous")
    assessment = judge.evaluate(query="tell me about it", evidence=[], current_plan=plan)

    assert assessment.decision == "clarification"


def test_judge_empty_evidence_insufficient_vs_abstain():
    judge = EvidenceJudge()
    plan = AcquisitionPlan(action="vector_search", reason_code="search")

    # Pass 1: empty evidence -> insufficient (budget remains)
    assessment1 = judge.evaluate(
        query="what is our revenue",
        evidence=[],
        current_plan=plan,
        retrieval_iterations=1,
        max_iterations=3,
    )
    assert assessment1.decision == "insufficient"
    assert assessment1.recommended_next_action == "refine_query"

    # Pass 3: empty evidence -> abstain (budget exhausted)
    assessment2 = judge.evaluate(
        query="what is our revenue",
        evidence=[],
        current_plan=plan,
        retrieval_iterations=3,
        max_iterations=3,
    )
    assert assessment2.decision == "abstain"


def test_judge_sufficient_evidence():
    judge = EvidenceJudge()
    evidence = [
        EvidenceItem(
            evidence_id="ev_1",
            source_type="document",
            source_id="d1",
            content="Our refund policy allows complete returns within thirty days.",
            retrieval_method="vector",
            retrieval_score=0.92,
        )
    ]

    assessment = judge.evaluate(
        query="what is the refund policy",
        evidence=evidence,
        current_plan=None,
    )
    assert assessment.decision == "sufficient"
    assert assessment.coverage_score >= 0.8


def test_judge_summary_request_with_retrieved_evidence():
    judge = EvidenceJudge()
    evidence = [
        EvidenceItem(
            evidence_id="ev_1",
            source_type="document",
            source_id="d1",
            content="The project reduces energy usage through adaptive load control.",
            retrieval_method="vector",
            retrieval_score=0.42,
        )
    ]

    assessment = judge.evaluate(
        query="can you summarise this file?",
        evidence=evidence,
        current_plan=None,
        retrieval_iterations=1,
        max_iterations=3,
    )

    assert assessment.decision == "sufficient"
    assert assessment.reason_code == "summary_request_with_retrieved_evidence"


def test_judge_conflicting_evidence():
    judge = EvidenceJudge()
    evidence = [
        EvidenceItem(
            evidence_id="ev_1",
            source_type="document",
            source_id="d1",
            content="Returns are allowed within 30 days.",
            metadata={"tags": ["conflict"]},
            retrieval_method="vector",
            retrieval_score=0.8,
        ),
        EvidenceItem(
            evidence_id="ev_2",
            source_type="document",
            source_id="d2",
            content="All sales are final. No returns under any condition.",
            metadata={"tags": ["conflict"]},
            retrieval_method="vector",
            retrieval_score=0.8,
        ),
    ]

    assessment = judge.evaluate(
        query="can I return items",
        evidence=evidence,
        current_plan=None,
        retrieval_iterations=1,
        max_iterations=3,
    )
    assert assessment.decision == "conflicting"
    assert len(assessment.conflict_groups) > 0


def test_judge_summary_query_different_vocabulary():
    """Verify 'what does the uploaded files tell us about?' is treated as summary/synthesis without literal keyword matching."""
    judge = EvidenceJudge()
    evidence = [
        EvidenceItem(
            evidence_id="ev_arch",
            source_type="document",
            source_id="doc_specs",
            content="The system consists of distributed workers managed by a coordinator node over gRPC.",
            retrieval_method="vector",
            retrieval_score=0.45,
        )
    ]

    assessment = judge.evaluate(
        query="what does the uploaded files tell us about?",
        evidence=evidence,
        current_plan=None,
    )
    assert assessment.decision == "sufficient"
    assert assessment.reason_code == "summary_request_with_retrieved_evidence"
    assert assessment.missing_aspects == []


def test_judge_advantages_query_with_synonyms():
    """Verify advantages query matches evidence containing 'benefits', 'strengths', or 'improvements'."""
    judge = EvidenceJudge()
    evidence = [
        EvidenceItem(
            evidence_id="ev_adv",
            source_type="document",
            source_id="d1",
            content="The new architecture provides key operational benefits and notable latency improvements.",
            retrieval_method="vector",
            retrieval_score=0.65,
        )
    ]

    assessment = judge.evaluate(
        query="what are the positive sides or advantages of this system?",
        evidence=evidence,
        current_plan=None,
    )
    assert assessment.decision == "sufficient"
    assert assessment.reason_code == "advantages_request_with_retrieved_evidence"
    assert assessment.missing_aspects == []


def test_judge_limitations_query_with_synonyms():
    """Verify limitations query matches evidence containing 'risks', 'weaknesses', or 'constraints'."""
    judge = EvidenceJudge()
    evidence = [
        EvidenceItem(
            evidence_id="ev_lim",
            source_type="document",
            source_id="d1",
            content="Under peak load, memory constraints and potential throughput risks may occur.",
            retrieval_method="vector",
            retrieval_score=0.62,
        )
    ]

    assessment = judge.evaluate(
        query="what are the limitations and weaknesses?",
        evidence=evidence,
        current_plan=None,
    )
    assert assessment.decision == "sufficient"
    assert assessment.reason_code == "limitations_request_with_retrieved_evidence"
    assert assessment.missing_aspects == []


def test_judge_findings_query_with_synonyms():
    """Verify findings query matches evidence containing 'results', 'conclusions', or 'demonstrated'."""
    judge = EvidenceJudge()
    evidence = [
        EvidenceItem(
            evidence_id="ev_find",
            source_type="document",
            source_id="d1",
            content="The study demonstrated a 35% reduction in error rates and confirmed key conclusions.",
            retrieval_method="vector",
            retrieval_score=0.60,
        )
    ]

    assessment = judge.evaluate(
        query="what are the main findings?",
        evidence=evidence,
        current_plan=None,
    )
    assert assessment.decision == "sufficient"
    assert assessment.reason_code == "findings_request_with_retrieved_evidence"
    assert assessment.missing_aspects == []


def test_judge_synthesis_query_multi_document():
    """Verify cross-document comparison query succeeds when evidence spans multiple documents."""
    judge = EvidenceJudge()
    evidence = [
        EvidenceItem(
            evidence_id="ev_r1",
            source_type="document",
            source_id="review_a",
            document_id="doc_a",
            content="Review A noted excellent build quality.",
            retrieval_method="vector",
            retrieval_score=0.55,
        ),
        EvidenceItem(
            evidence_id="ev_r2",
            source_type="document",
            source_id="review_b",
            document_id="doc_b",
            content="Review B highlighted battery life differences.",
            retrieval_method="vector",
            retrieval_score=0.58,
        ),
    ]

    assessment = judge.evaluate(
        query="compare the two reviews",
        evidence=evidence,
        current_plan=None,
    )
    assert assessment.decision == "sufficient"
    assert assessment.reason_code == "synthesis_request_with_retrieved_evidence"


def test_judge_stopwords_never_in_missing_aspects():
    """Verify generic stopwords are never included in missing_aspects on low coverage."""
    from application.evidence_judge import STOPWORDS

    judge = EvidenceJudge()
    evidence = [
        EvidenceItem(
            evidence_id="ev_unrelated",
            source_type="document",
            source_id="d1",
            content="Completely unrelated passage about maritime shipping schedules.",
            retrieval_method="vector",
            retrieval_score=0.10,
        )
    ]

    assessment = judge.evaluate(
        query="what does this uploaded file tell us about quantum supercomputing?",
        evidence=evidence,
        current_plan=None,
        retrieval_iterations=1,
        max_iterations=3,
    )

    for aspect in assessment.missing_aspects:
        assert aspect.lower() not in STOPWORDS, f"Stopword '{aspect}' found in missing_aspects!"
        assert aspect.lower() not in {
            "what", "does", "this", "uploaded", "file", "tell", "us", "about"
        }
