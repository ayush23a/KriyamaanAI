import json
import logging
import uuid
from pathlib import Path
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from evaluation.metrics import compute_case_scores
from persistence.models import EvaluationCaseModel, EvaluationRunModel

logger = logging.getLogger(__name__)


class EvaluationRunner:
    """Repeatable runner for offline and regression evaluation datasets."""

    def __init__(self, dataset_path: str | Path | None = None):
        if dataset_path:
            self.dataset_path = Path(dataset_path)
        else:
            self.dataset_path = (
                Path(__file__).resolve().parent / "datasets" / "default_benchmark_v1.jsonl"
            )

    def load_dataset(self) -> list[dict[str, Any]]:
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found at {self.dataset_path}")
        cases = []
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    cases.append(json.loads(line))
        return cases

    async def evaluate_case(
        self,
        case: dict[str, Any],
        service: Any = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Execute a single evaluation case and calculate metrics."""
        case_id = case["case_id"]
        query = case["query"]
        expected_behavior = case.get("expected_behavior", "answer")
        reference_ids = case.get("reference_context_ids", [])

        # Default mock evaluation output if no live service is injected
        if service is None:
            # Deterministic simulation based on expected behavior
            if expected_behavior == "abstain":
                status = "abstention"
                answer_text = ""
                evidence_texts: list[str] = []
                retrieved_ids: list[str] = []
            elif expected_behavior == "clarify":
                status = "clarification"
                answer_text = "Could you please clarify your request?"
                evidence_texts = []
                retrieved_ids = []
            else:
                status = "answer"
                docs = case.get("documents", [])
                evidence_texts = [d.get("content", "") for d in docs]
                retrieved_ids = [d.get("id", "") for d in docs]
                answer_text = case.get("reference_answer", "Supported factual answer.")
        else:
            # Use injected service to execute real or mock graph
            result = await service.execute_case(case)
            status = result.get("status", "answer")
            answer_text = result.get("answer_text", "")
            evidence_texts = result.get("evidence_texts", [])
            retrieved_ids = result.get("retrieved_ids", [])

        scores = compute_case_scores(
            query=query,
            answer_text=answer_text,
            status=status,
            evidence_texts=evidence_texts,
            retrieved_ids=retrieved_ids,
            reference_ids=reference_ids,
            expected_behavior=expected_behavior,
        )

        return {
            "case_id": case_id,
            "status": status,
            "answer_text": answer_text,
            "scores": scores,
            "input": case,
        }

    async def run(
        self,
        dataset_name: str = "default_benchmark",
        version: str = "v1",
        service: Any = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Run full evaluation suite across the dataset and aggregate results."""
        cases = self.load_dataset()
        eval_run_id = str(uuid.uuid4())
        results = []

        total_faithfulness = 0.0
        total_relevancy = 0.0
        total_recall = 0.0
        total_precision = 0.0
        total_abstention = 0.0
        total_budget = 0.0
        total_overall = 0.0

        for case in cases:
            res = await self.evaluate_case(case, service=service, db=db)
            results.append(res)
            scores = res["scores"]
            total_faithfulness += scores["faithfulness"]
            total_relevancy += scores["answer_relevancy"]
            total_recall += scores["context_recall"]
            total_precision += scores["context_precision"]
            total_abstention += scores["abstention_quality"]
            total_budget += scores["budget_adherence"]
            total_overall += scores["overall_score"]

        n = len(cases) or 1
        aggregated_scores = {
            "mean_faithfulness": round(total_faithfulness / n, 4),
            "mean_answer_relevancy": round(total_relevancy / n, 4),
            "mean_context_recall": round(total_recall / n, 4),
            "mean_context_precision": round(total_precision / n, 4),
            "mean_abstention_quality": round(total_abstention / n, 4),
            "mean_budget_adherence": round(total_budget / n, 4),
            "mean_overall_score": round(total_overall / n, 4),
            "total_cases": n,
        }

        # Persist if a database session was supplied
        if db is not None:
            run_model = EvaluationRunModel(
                id=eval_run_id,
                dataset_name=dataset_name,
                dataset_version=version,
                config_json={"dataset_path": str(self.dataset_path)},
                status="completed",
                scores_json=aggregated_scores,
            )
            db.add(run_model)
            await db.flush()

            for r in results:
                case_model = EvaluationCaseModel(
                    evaluation_run_id=eval_run_id,
                    case_id=r["case_id"],
                    input_json=r["input"],
                    output_json={"status": r["status"], "answer_text": r["answer_text"]},
                    scores_json=r["scores"],
                )
                db.add(case_model)
            await db.flush()

        return {
            "evaluation_run_id": eval_run_id,
            "dataset_name": dataset_name,
            "dataset_version": version,
            "aggregated_scores": aggregated_scores,
            "case_results": results,
        }
