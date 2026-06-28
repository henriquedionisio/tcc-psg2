from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml
from sqlmodel import Session, select

from src.database import get_session, init_db
from src.metrics.runner import MetricsRunner
from src.models.entities import (
    Conversation,
    ConversationCategory,
    ExperimentRun,
    Message,
    MessageRole,
    Twin,
)
from src.services.cost_tracker import CostTracker
from src.services.fork import ForkService
from src.services.llm import LLMService
from src.services.user_simulator import UserSimulator


class ExperimentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.cost_tracker = CostTracker()
        self.llm = LLMService(self.cost_tracker)
        self.fork_service = ForkService(session)
        self.user_simulator = UserSimulator(self.llm)

    def load_config(self, config_path: str) -> dict:
        path = Path(config_path)
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load_conversation_def(self, conv_path: str) -> dict:
        path = Path(conv_path)
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)

    @staticmethod
    def _format_constraints(conv_def: dict) -> str:
        raw = conv_def.get("constraints")
        if not raw:
            return ""
        if isinstance(raw, list):
            return "\n".join(f"- {item}" for item in raw)
        return str(raw)

    def seed_conversation(self, conv_def: dict) -> Conversation:
        constraints = self._format_constraints(conv_def)
        difficulty = conv_def.get("difficulty", "simple")
        existing = self.session.exec(
            select(Conversation).where(Conversation.external_id == conv_def["id"])
        ).first()

        if existing:
            existing.category = ConversationCategory(conv_def["category"])
            existing.title = conv_def["title"]
            existing.objective = conv_def["objective"]
            existing.constraints = constraints
            existing.difficulty = difficulty
            self.session.add(existing)

            seed_messages = list(
                self.session.exec(
                    select(Message).where(
                        Message.conversation_id == existing.id,
                        Message.twin_id.is_(None),
                    )
                ).all()
            )
            for msg in seed_messages:
                self.session.delete(msg)
            self.session.commit()
            conversation = existing
        else:
            conversation = Conversation(
                external_id=conv_def["id"],
                category=ConversationCategory(conv_def["category"]),
                title=conv_def["title"],
                objective=conv_def["objective"],
                constraints=constraints,
                difficulty=difficulty,
            )
            self.session.add(conversation)
            self.session.commit()
            self.session.refresh(conversation)

        for msg in conv_def.get("seed_messages", []):
            message = Message(
                conversation_id=conversation.id,
                role=MessageRole(msg["role"]),
                content=msg["content"],
                turn_number=msg["turn"],
            )
            self.session.add(message)
        self.session.commit()
        self.session.refresh(conversation)
        return conversation

    def run_twin_continuation(
        self,
        twin: Twin,
        conversation: Conversation,
        max_turns_post_fork: int,
        max_tokens_per_response: int,
        stop_on_user_intent: bool = True,
        max_history_messages: int = 18,
    ) -> Twin:
        current_turn = twin.fork_turn
        post_fork_turns = 0

        while post_fork_turns < max_turns_post_fork:
            history = self.fork_service.get_twin_messages(twin.id)
            if not history:
                break

            user_content = self.user_simulator.generate_user_message(
                objective=conversation.objective,
                category=conversation.category,
                history=history[-max_history_messages:],
                constraints=conversation.constraints,
            )
            current_turn += 1
            user_msg = Message(
                conversation_id=conversation.id,
                twin_id=twin.id,
                role=MessageRole.USER,
                content=user_content,
                turn_number=current_turn,
            )
            self.session.add(user_msg)
            self.session.commit()

            if stop_on_user_intent and self.user_simulator.should_stop(user_content):
                twin.resolved = True
                twin.stopped_reason = "user_intent"
                twin.total_turns = post_fork_turns + 1
                self.session.add(twin)
                self.session.commit()
                break

            chat_history = [
                {"role": m.role.value, "content": m.content}
                for m in self.fork_service.get_twin_messages(twin.id)
                if m.role != MessageRole.SYSTEM
            ][:-1]

            response = self.llm.chat(
                messages=chat_history,
                system_prompt=twin.system_prompt,
                temperature=twin.temperature,
                top_p=twin.top_p,
                max_tokens=max_tokens_per_response,
                max_history_messages=max_history_messages,
            )

            current_turn += 1
            assistant_msg = Message(
                conversation_id=conversation.id,
                twin_id=twin.id,
                role=MessageRole.ASSISTANT,
                content=response.content,
                turn_number=current_turn,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                total_tokens=response.total_tokens,
            )
            self.session.add(assistant_msg)

            twin.total_turns = post_fork_turns + 1
            twin.total_tokens += response.total_tokens + user_msg.total_tokens
            self.session.add(twin)
            self.session.commit()

            post_fork_turns += 1

        if not twin.stopped_reason and post_fork_turns >= max_turns_post_fork:
            twin.stopped_reason = "max_turns"
            self.session.add(twin)
            self.session.commit()

        return twin

    def _run_single_replication(
        self,
        config: dict,
        config_path: str,
        replication_index: int,
        dry_run: bool,
    ) -> ExperimentRun:
        exp_config = config.get("experiment", {})
        limits = config.get("limits", {})

        max_turns_post_fork = limits.get("max_turns_post_fork", 5)
        max_tokens = limits.get("max_tokens_per_response", 500)
        max_history_messages = limits.get("max_history_messages", 18)
        fork_turns = exp_config.get("fork_turns", [3, 6])
        conversations = config.get("conversations", [])
        stop_on_user_intent = limits.get("stop_on_user_intent", True)
        include_control_replicate = limits.get("include_control_replicate", True)

        if dry_run:
            conversations = conversations[:1]
            fork_turns = fork_turns[:1]

        base_name = exp_config.get("name", "poc")
        run_name = base_name if replication_index == 1 and exp_config.get("replications", 1) == 1 else (
            f"{base_name}_rep{replication_index}"
        )

        experiment = ExperimentRun(
            name=run_name,
            config_path=config_path,
            replication_index=replication_index,
            dry_run=dry_run,
            status="running",
            started_at=datetime.utcnow(),
        )
        self.session.add(experiment)
        self.session.commit()
        self.session.refresh(experiment)

        try:
            for conv_entry in conversations:
                conv_def = self.load_conversation_def(conv_entry["path"])
                conversation = self.seed_conversation(conv_def)

                for fork_turn in fork_turns:
                    twins = self.fork_service.spawn_twins_for_fork(
                        conversation=conversation,
                        experiment_run_id=experiment.id,
                        fork_turn=fork_turn,
                        max_twins=3 if dry_run else None,
                        include_control_replicate=include_control_replicate,
                    )

                    for twin in twins:
                        self.run_twin_continuation(
                            twin=twin,
                            conversation=conversation,
                            max_turns_post_fork=max_turns_post_fork,
                            max_tokens_per_response=max_tokens,
                            stop_on_user_intent=stop_on_user_intent,
                            max_history_messages=max_history_messages,
                        )

            metrics_runner = MetricsRunner(
                self.session,
                self.llm,
                judge_sample_rate=limits.get("judge_sample_rate", 0.5),
            )
            metrics_runner.evaluate_experiment(experiment.id)

            experiment.status = "completed"
            experiment.finished_at = datetime.utcnow()
            experiment.total_api_calls = self.cost_tracker.api_calls
            experiment.total_tokens = self.cost_tracker.total_tokens
            experiment.estimated_cost_usd = self.cost_tracker.estimated_cost_usd
            self.session.add(experiment)
            self.session.commit()
            self.session.refresh(experiment)
            return experiment

        except Exception as exc:
            experiment.status = f"failed: {exc}"
            experiment.finished_at = datetime.utcnow()
            experiment.total_api_calls = self.cost_tracker.api_calls
            experiment.total_tokens = self.cost_tracker.total_tokens
            experiment.estimated_cost_usd = self.cost_tracker.estimated_cost_usd
            self.session.add(experiment)
            self.session.commit()
            raise

    def run_experiment(
        self,
        config_path: str,
        dry_run: bool = False,
        start_replication: int = 1,
    ) -> ExperimentRun:
        init_db()
        config = self.load_config(config_path)
        exp_config = config.get("experiment", {})
        replications = 1 if dry_run else exp_config.get("replications", 1)
        start_replication = max(1, start_replication)

        last_run: ExperimentRun | None = None
        for replication_index in range(start_replication, replications + 1):
            self.cost_tracker.reset()
            last_run = self._run_single_replication(
                config=config,
                config_path=config_path,
                replication_index=replication_index,
                dry_run=dry_run,
            )

        if last_run is None:
            raise RuntimeError("Nenhuma replicação foi executada")
        return last_run


def run_experiment_from_config(
    config_path: str,
    dry_run: bool = False,
    start_replication: int = 1,
) -> int:
    with get_session() as session:
        service = ExperimentService(session)
        result = service.run_experiment(
            config_path,
            dry_run=dry_run,
            start_replication=start_replication,
        )
        return result.id
