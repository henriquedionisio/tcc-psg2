from __future__ import annotations

import random

from sqlmodel import Session, select

from src.metrics.base import MetricContext
from src.metrics.divergence import AttributedDivergenceMetric, IntrinsicDivergenceMetric
from src.metrics.llm_judge import AdequacaoMetric, FactualidadeMetric, RobustezMetric
from src.metrics.resolution import ResolutionMetric
from src.metrics.tokens import TokensMetric
from src.metrics.turns import TurnsMetric
from src.models.entities import Conversation, MetricResult, Twin, TwinType
from src.services.fork import ForkService
from src.services.llm import LLMService


class MetricsRunner:
    def __init__(self, session: Session, llm: LLMService, judge_sample_rate: float = 0.5) -> None:
        self.session = session
        self.llm = llm
        self.judge_sample_rate = judge_sample_rate
        self.fork_service = ForkService(session)
        self.auto_metrics = [TokensMetric(), TurnsMetric()]
        self.judge_metrics = [
            ResolutionMetric(llm),
            FactualidadeMetric(llm),
            RobustezMetric(llm),
            AdequacaoMetric(llm),
        ]
        self.intrinsic_metric = IntrinsicDivergenceMetric(llm)
        self.attributed_metric = AttributedDivergenceMetric()

    def _get_control_a(self, conversation_id: int, fork_turn: int, experiment_run_id: int) -> Twin | None:
        query = select(Twin).where(
            Twin.conversation_id == conversation_id,
            Twin.fork_turn == fork_turn,
            Twin.experiment_run_id == experiment_run_id,
            Twin.twin_type == TwinType.CONTROL,
        )
        return self.session.exec(query).first()

    def _get_control_replicate(
        self, conversation_id: int, fork_turn: int, experiment_run_id: int
    ) -> Twin | None:
        query = select(Twin).where(
            Twin.conversation_id == conversation_id,
            Twin.fork_turn == fork_turn,
            Twin.experiment_run_id == experiment_run_id,
            Twin.twin_type == TwinType.CONTROL_REPLICATE,
        )
        return self.session.exec(query).first()

    def _last_assistant_content(self, twin_id: int) -> str | None:
        messages = self.fork_service.get_twin_messages(twin_id)
        assistant = next((m for m in reversed(messages) if m.role.value == "assistant"), None)
        return assistant.content if assistant else None

    def _save_metric(self, twin_id: int, experiment_run_id: int, evaluated) -> MetricResult:
        result = MetricResult(
            twin_id=twin_id,
            experiment_run_id=experiment_run_id,
            metric_name=evaluated.metric_name,
            score=evaluated.score,
            value=evaluated.value,
            details=evaluated.details,
        )
        self.session.add(result)
        return result

    def _get_intrinsic_divergence_pct(
        self, conversation_id: int, fork_turn: int, experiment_run_id: int
    ) -> float | None:
        replicate = self._get_control_replicate(conversation_id, fork_turn, experiment_run_id)
        if not replicate:
            return None
        metric = self.session.exec(
            select(MetricResult).where(
                MetricResult.twin_id == replicate.id,
                MetricResult.experiment_run_id == experiment_run_id,
                MetricResult.metric_name == "intrinsic_divergence_pct",
            )
        ).first()
        return metric.score if metric and metric.score is not None else None

    def evaluate_twin(self, twin: Twin, conversation: Conversation, experiment_run_id: int) -> list[MetricResult]:
        messages = self.fork_service.get_twin_messages(twin.id)
        if not messages:
            return []

        last_user = next((m for m in reversed(messages) if m.role.value == "user"), None)
        last_assistant = next((m for m in reversed(messages) if m.role.value == "assistant"), None)
        if not last_user or not last_assistant:
            return []

        control_a = self._get_control_a(conversation.id, twin.fork_turn, experiment_run_id)
        baseline_message = None
        if control_a and control_a.id != twin.id:
            baseline_message = self._last_assistant_content(control_a.id)

        context = MetricContext(
            twin_id=twin.id,
            twin_label=twin.label,
            twin_type=twin.twin_type.value,
            objective=conversation.objective,
            category=conversation.category.value,
            fork_turn=twin.fork_turn,
            user_message=last_user.content,
            assistant_message=last_assistant.content,
            baseline_message=baseline_message,
            total_turns=twin.total_turns,
            total_tokens=twin.total_tokens,
        )

        results: list[MetricResult] = []
        for metric in self.auto_metrics:
            results.append(
                self._save_metric(twin.id, experiment_run_id, metric.evaluate(context))
            )

        run_judge = (
            twin.twin_type in (TwinType.CONTROL, TwinType.CONTROL_REPLICATE)
            or random.random() < self.judge_sample_rate
        )

        total_robustez: float | None = None

        if twin.twin_type == TwinType.CONTROL_REPLICATE and baseline_message:
            intrinsic = self.intrinsic_metric.evaluate(context)
            results.append(self._save_metric(twin.id, experiment_run_id, intrinsic))

        if run_judge:
            for metric in self.judge_metrics:
                if metric.name == "robustez" and twin.twin_type in (
                    TwinType.CONTROL,
                    TwinType.CONTROL_REPLICATE,
                ):
                    continue
                evaluated = metric.evaluate(context)
                if metric.name == "robustez" and evaluated.score is not None:
                    total_robustez = evaluated.score
                results.append(self._save_metric(twin.id, experiment_run_id, evaluated))

        if twin.twin_type in (TwinType.PROMPT, TwinType.PARAMETER) and total_robustez is not None:
            intrinsic_pct = self._get_intrinsic_divergence_pct(
                conversation.id, twin.fork_turn, experiment_run_id
            )
            attributed = self.attributed_metric.evaluate(context, total_robustez, intrinsic_pct)
            results.append(self._save_metric(twin.id, experiment_run_id, attributed))

        self.session.commit()
        return results

    def evaluate_experiment(self, experiment_run_id: int) -> int:
        twins = list(
            self.session.exec(
                select(Twin).where(Twin.experiment_run_id == experiment_run_id)
            ).all()
        )
        replicate_twins = [t for t in twins if t.twin_type == TwinType.CONTROL_REPLICATE]
        other_twins = [t for t in twins if t.twin_type != TwinType.CONTROL_REPLICATE]

        count = 0
        for twin in replicate_twins + other_twins:
            conversation = self.session.get(Conversation, twin.conversation_id)
            if conversation:
                self.evaluate_twin(twin, conversation, experiment_run_id)
                count += 1
        return count
