from __future__ import annotations

import json

from src.metrics.base import BaseMetric, EvaluatedMetric, MetricContext
from src.services.llm import LLMService, load_prompt


class ResolutionMetric(BaseMetric):
    name = "resolution"

    def __init__(self, llm: LLMService) -> None:
        self.llm = llm
        self.template = load_prompt("judge_resolucao.txt")

    def evaluate(self, context: MetricContext) -> EvaluatedMetric:
        response = self.llm.judge(
            self.template,
            {
                "objective": context.objective,
                "user_message": context.user_message,
                "assistant_message": context.assistant_message,
            },
        )
        try:
            data = json.loads(response.content)
            resolved = data.get("resolved", False)
            return EvaluatedMetric(
                metric_name=self.name,
                score=1.0 if resolved else 0.0,
                value="resolved" if resolved else "unresolved",
                details=data.get("justification", response.content),
            )
        except json.JSONDecodeError:
            return EvaluatedMetric(
                metric_name=self.name,
                score=0.0,
                value="unresolved",
                details=response.content,
            )
