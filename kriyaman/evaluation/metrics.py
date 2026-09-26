import re
from typing import Any


def calculate_token_overlap(text_a: str, text_b: str) -> float:
    """Calculate normalized token overlap (Jaccard similarity) between two texts."""
    tokens_a = set(re.findall(r"\w+", text_a.lower()))
    tokens_b = set(re.findall(r"\w+", text_b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union)


def evaluate_faithfulness(answer_text: str, evidence_texts: list[str]) -> float:
    """Measure the degree to which claims in the answer are grounded in retrieved evidence."""
    if not answer_text.strip():
        return 1.0  # Safe abstention is faithful
    if not evidence_texts:
        return 0.0  # Answer with zero evidence is ungrounded
    combined_evidence = " ".join(evidence_texts)
    sentences = [s.strip() for s in re.split(r"[.!?]", answer_text) if len(s.strip()) > 5]
    if not sentences:
        return 1.0
    grounded = 0
    for s in sentences:
        if calculate_token_overlap(s, combined_evidence) > 0.15:
            grounded += 1
    return round(grounded / len(sentences), 4)


STOP_WORDS = {
    "what", "is", "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "as", "are", "was", "were", "be", "this", "that", "it", "how", "why", "when"
}


def evaluate_answer_relevancy(query: str, answer_text: str) -> float:
    """Measure how directly the answer addresses the user query based on content terms."""
    if not answer_text.strip():
        return 0.5
    query_tokens = [t for t in re.findall(r"\w+", query.lower()) if t not in STOP_WORDS]
    if not query_tokens:
        return 1.0
    ans_tokens = set(re.findall(r"\w+", answer_text.lower()))
    matches = sum(1 for t in query_tokens if t in ans_tokens)
    return round(matches / len(query_tokens), 4)


def evaluate_context_recall(retrieved_ids: list[str], reference_ids: list[str]) -> float:
    """Measure fraction of reference context IDs that were successfully retrieved."""
    if not reference_ids:
        return 1.0
    found = [r_id for r_id in reference_ids if r_id in retrieved_ids]
    return round(len(found) / len(reference_ids), 4)


def evaluate_context_precision(retrieved_ids: list[str], reference_ids: list[str]) -> float:
    """Measure ranking quality and precision of retrieved context IDs."""
    if not retrieved_ids:
        return 1.0 if not reference_ids else 0.0
    if not reference_ids:
        return 1.0
    hits = [1 if r_id in reference_ids else 0 for r_id in retrieved_ids]
    if sum(hits) == 0:
        return 0.0
    # Mean Average Precision approximation
    score = 0.0
    running_hits = 0
    for idx, hit in enumerate(hits):
        if hit:
            running_hits += 1
            score += running_hits / (idx + 1)
    return round(score / len(reference_ids), 4)


def evaluate_abstention_quality(status: str, expected_behavior: str) -> float:
    """Measure correctness of abstention or clarification decisions."""
    if expected_behavior == "abstain":
        return 1.0 if status == "abstention" else 0.0
    if expected_behavior == "clarify":
        return 1.0 if status in ("clarification", "abstention") else 0.5
    if expected_behavior == "answer":
        return 1.0 if status == "answer" else 0.0
    return 1.0


def evaluate_budget_adherence(
    iterations: int,
    tool_calls: int,
    max_iterations: int = 3,
    max_tools: int = 3,
) -> float:
    """Check whether the run stayed strictly within configured execution budgets."""
    adheres = (iterations <= max_iterations) and (tool_calls <= max_tools)
    return 1.0 if adheres else 0.0


def compute_case_scores(
    query: str,
    answer_text: str,
    status: str,
    evidence_texts: list[str],
    retrieved_ids: list[str],
    reference_ids: list[str],
    expected_behavior: str,
    iterations: int = 1,
    tool_calls: int = 0,
) -> dict[str, float]:
    """Compute complete suite of Ragas and custom Agentic-RAG metrics for a test case."""
    faithfulness = evaluate_faithfulness(answer_text, evidence_texts)
    relevancy = evaluate_answer_relevancy(query, answer_text)
    recall = evaluate_context_recall(retrieved_ids, reference_ids)
    precision = evaluate_context_precision(retrieved_ids, reference_ids)
    abstention = evaluate_abstention_quality(status, expected_behavior)
    budget = evaluate_budget_adherence(iterations, tool_calls)

    overall = round(
        (faithfulness * 0.25)
        + (relevancy * 0.25)
        + (recall * 0.15)
        + (precision * 0.15)
        + (abstention * 0.10)
        + (budget * 0.10),
        4,
    )

    return {
        "faithfulness": faithfulness,
        "answer_relevancy": relevancy,
        "context_recall": recall,
        "context_precision": precision,
        "abstention_quality": abstention,
        "budget_adherence": budget,
        "overall_score": overall,
    }
