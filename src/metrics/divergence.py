from __future__ import annotations

from src.metrics.base import BaseMetric, EvaluatedMetric, MetricContext
from src.metrics.llm_judge import RobustezMetric
from src.services.llm import LLMService


def robustez_to_divergence_pct(robustez_score: float) -> float:
    """Converte robustez 1–5 em divergência percentual (5=0%, 1=100%)."""
    return max(0.0, min(100.0, (5.0 - robustez_score) / 4.0 * 100.0))


class IntrinsicDivergenceMetric(BaseMetric):
    """Divergência entre controle A e réplica idêntica B (ruído intrínseco)."""

    name = "intrinsic_divergence_pct"

    def __init__(self, llm: LLMService) -> None:
        self.robustez = RobustezMetric(llm)

    def evaluate(self, context: MetricContext) -> EvaluatedMetric:
        if not context.baseline_message:
            return EvaluatedMetric(
                metric_name=self.name,
                score=None,
                value="skipped",
                details="Sem controle A para comparar",
            )
        evaluated = self.robustez.evaluate(context)
        if evaluated.score is None:
            return EvaluatedMetric(
                metric_name=self.name,
                score=None,
                value=evaluated.value,
                details=evaluated.details,
            )
        divergence = robustez_to_divergence_pct(evaluated.score)
        return EvaluatedMetric(
            metric_name=self.name,
            score=divergence,
            value=f"{divergence:.1f}%",
            details=(
                f"Ruído intrínseco A/B: robustez={evaluated.score:.1f} "
                f"→ divergência={divergence:.1f}%. {evaluated.details or ''}"
            ),
        )


class AttributedDivergenceMetric(BaseMetric):
    """Divergência atribuível à perturbação = total − ruído intrínseco."""

    name = "attributed_divergence_pct"

    def evaluate(
        self,
        context: MetricContext,
        total_robustez: float | None,
        intrinsic_divergence_pct: float | None,
    ) -> EvaluatedMetric:
        if total_robustez is None:
            return EvaluatedMetric(
                metric_name=self.name,
                score=None,
                value="skipped",
                details="Sem robustez total vs. controle A",
            )
        if intrinsic_divergence_pct is None:
            return EvaluatedMetric(
                metric_name=self.name,
                score=None,
                value="skipped",
                details="Sem baseline intrínseco A/B neste fork",
            )
        total_pct = robustez_to_divergence_pct(total_robustez)
        attributed = max(0.0, total_pct - intrinsic_divergence_pct)
        return EvaluatedMetric(
            metric_name=self.name,
            score=attributed,
            value=f"{attributed:.1f}%",
            details=(
                f"Total={total_pct:.1f}% − intrínseco={intrinsic_divergence_pct:.1f}% "
                f"= atribuível={attributed:.1f}%"
            ),
        )
