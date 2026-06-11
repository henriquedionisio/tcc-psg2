from __future__ import annotations

from src.metrics.base import BaseMetric, EvaluatedMetric, MetricContext


class TokensMetric(BaseMetric):
    name = "tokens"

    def evaluate(self, context: MetricContext) -> EvaluatedMetric:
        return EvaluatedMetric(
            metric_name=self.name,
            score=float(context.total_tokens),
            value=str(context.total_tokens),
            details=f"Total tokens consumidos pelo twin {context.twin_label}",
        )
