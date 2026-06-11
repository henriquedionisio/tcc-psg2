from __future__ import annotations

from src.metrics.base import BaseMetric, EvaluatedMetric, MetricContext


class TurnsMetric(BaseMetric):
    name = "turns"

    def evaluate(self, context: MetricContext) -> EvaluatedMetric:
        return EvaluatedMetric(
            metric_name=self.name,
            score=float(context.total_turns),
            value=str(context.total_turns),
            details=f"Turnos pós-fork do twin {context.twin_label}",
        )
