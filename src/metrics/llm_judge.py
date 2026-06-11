from __future__ import annotations

import json

from src.metrics.base import BaseMetric, EvaluatedMetric, MetricContext
from src.services.llm import LLMService, load_prompt


def _parse_judge_response(content: str, metric_name: str) -> EvaluatedMetric:
    try:
        data = json.loads(content)
        score = float(data.get("score", 0))
        return EvaluatedMetric(
            metric_name=metric_name,
            score=score,
            value=str(score),
            details=data.get("justification", content),
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        return EvaluatedMetric(
            metric_name=metric_name,
            score=None,
            value=None,
            details=content,
        )


class FactualidadeMetric(BaseMetric):
    name = "factualidade"

    def __init__(self, llm: LLMService) -> None:
        self.llm = llm
        self.template = load_prompt("judge_factualidade.txt")

    def evaluate(self, context: MetricContext) -> EvaluatedMetric:
        response = self.llm.judge(
            self.template,
            {
                "objective": context.objective,
                "user_message": context.user_message,
                "assistant_message": context.assistant_message,
            },
        )
        return _parse_judge_response(response.content, self.name)


class RobustezMetric(BaseMetric):
    name = "robustez"

    def __init__(self, llm: LLMService) -> None:
        self.llm = llm
        self.template = load_prompt("judge_robustez.txt")

    def evaluate(self, context: MetricContext) -> EvaluatedMetric:
        if not context.baseline_message:
            return EvaluatedMetric(
                metric_name=self.name,
                score=None,
                value="skipped",
                details="Sem baseline para comparação",
            )
        response = self.llm.judge(
            self.template,
            {
                "objective": context.objective,
                "user_message": context.user_message,
                "baseline_message": context.baseline_message,
                "twin_message": context.assistant_message,
            },
        )
        return _parse_judge_response(response.content, self.name)


class AdequacaoMetric(BaseMetric):
    name = "adequacao_institucional"

    def __init__(self, llm: LLMService) -> None:
        self.llm = llm
        self.template = load_prompt("judge_adequacao.txt")

    def evaluate(self, context: MetricContext) -> EvaluatedMetric:
        if context.category not in ("contextual", "instructional"):
            return EvaluatedMetric(
                metric_name=self.name,
                score=None,
                value="skipped",
                details="Métrica aplicável apenas a conversas contextual/instrucional",
            )
        response = self.llm.judge(
            self.template,
            {
                "objective": context.objective,
                "user_message": context.user_message,
                "assistant_message": context.assistant_message,
            },
        )
        return _parse_judge_response(response.content, self.name)
