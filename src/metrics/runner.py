from __future__ import annotations

import random

from sqlmodel import Session, select

from src.metrics.base import MetricContext
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

    def _get_control_twin(self, conversation_id: int, fork_turn: int, experiment_run_id: int) -> Twin | None:
        query = select(Twin).where(
            Twin.conversation_id == conversation_id,
            Twin.fork_turn == fork_turn,
            Twin.experiment_run_id == experiment_run_id,
            Twin.twin_type == TwinType.CONTROL,
        )
        return self.session.exec(query).first()

    def evaluate_twin(self, twin: Twin, conversation: Conversation, experiment_run_id: int) -> list[MetricResult]:
        messages = self.fork_service.get_twin_messages(twin.id)
        if not messages:
            return []

        last_user = next((m for m in reversed(messages) if m.role.value == "user"), None)
        last_assistant = next((m for m in reversed(messages) if m.role.value == "assistant"), None)
        if not last_user or not last_assistant:
            return []

        control = self._get_control_twin(conversation.id, twin.fork_turn, experiment_run_id)
        baseline_message = None
        if control and control.id != twin.id:
            control_msgs = self.fork_service.get_twin_messages(control.id)
            baseline_assistant = next(
                (m for m in reversed(control_msgs) if m.role.value == "assistant"), None
            )
            if baseline_assistant:
                baseline_message = baseline_assistant.content

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

        results = []
        for metric in self.auto_metrics:
            evaluated = metric.evaluate(context)
            result = MetricResult(
                twin_id=twin.id,
                experiment_run_id=experiment_run_id,
                metric_name=evaluated.metric_name,
                score=evaluated.score,
                value=evaluated.value,
                details=evaluated.details,
            )
            self.session.add(result)
            results.append(result)

        run_judge = twin.twin_type == TwinType.CONTROL or random.random() < self.judge_sample_rate
        if run_judge:
            for metric in self.judge_metrics:
                evaluated = metric.evaluate(context)
                result = MetricResult(
                    twin_id=twin.id,
                    experiment_run_id=experiment_run_id,
                    metric_name=evaluated.metric_name,
                    score=evaluated.score,
                    value=evaluated.value,
                    details=evaluated.details,
                )
                self.session.add(result)
                results.append(result)

        self.session.commit()
        return results

    def evaluate_experiment(self, experiment_run_id: int) -> int:
        twins = list(
            self.session.exec(
                select(Twin).where(Twin.experiment_run_id == experiment_run_id)
            ).all()
        )
        count = 0
        for twin in twins:
            conversation = self.session.get(Conversation, twin.conversation_id)
            if conversation:
                self.evaluate_twin(twin, conversation, experiment_run_id)
                count += 1
        return count
