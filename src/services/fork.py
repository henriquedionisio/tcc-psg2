from __future__ import annotations

from sqlmodel import Session, select

from src.models.entities import Conversation, Message, MessageRole, Twin, TwinType
from src.services.llm import load_prompt


PROMPT_VARIANTS = {
    "baseline": "system_baseline.txt",
    "simple": "system_simple.txt",
    "medium": "system_medium.txt",
    "complex": "system_complex.txt",
}

PARAM_COMBINATIONS = [
    {"label": "deterministic", "temperature": 0.0, "top_p": 1.0},
    {"label": "baseline_params", "temperature": 0.7, "top_p": 1.0},
    {"label": "high_temp_restricted", "temperature": 1.0, "top_p": 0.4},
    {"label": "max_variability", "temperature": 1.0, "top_p": 1.0},
]


class ForkService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_messages_until_turn(
        self, conversation_id: int, fork_turn: int, twin_id: int | None = None
    ) -> list[Message]:
        query = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.turn_number <= fork_turn,
        )
        if twin_id is None:
            query = query.where(Message.twin_id.is_(None))
        else:
            query = query.where(Message.twin_id == twin_id)
        query = query.order_by(Message.turn_number)
        return list(self.session.exec(query).all())

    def create_twin(
        self,
        conversation_id: int,
        experiment_run_id: int,
        fork_turn: int,
        twin_type: TwinType,
        label: str,
        temperature: float = 0.7,
        top_p: float = 1.0,
        system_prompt_name: str = "baseline",
        parent_twin_id: int | None = None,
    ) -> Twin:
        system_prompt = load_prompt(PROMPT_VARIANTS.get(system_prompt_name, PROMPT_VARIANTS["baseline"]))
        twin = Twin(
            conversation_id=conversation_id,
            experiment_run_id=experiment_run_id,
            parent_twin_id=parent_twin_id,
            twin_type=twin_type,
            label=label,
            fork_turn=fork_turn,
            temperature=temperature,
            top_p=top_p,
            system_prompt_name=system_prompt_name,
            system_prompt=system_prompt,
        )
        self.session.add(twin)
        self.session.commit()
        self.session.refresh(twin)
        return twin

    def copy_history_to_twin(self, conversation_id: int, twin: Twin) -> list[Message]:
        source_messages = self.get_messages_until_turn(conversation_id, twin.fork_turn)
        copied = []
        for msg in source_messages:
            if msg.role == MessageRole.SYSTEM:
                continue
            new_msg = Message(
                conversation_id=conversation_id,
                twin_id=twin.id,
                role=msg.role,
                content=msg.content,
                turn_number=msg.turn_number,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            )
            self.session.add(new_msg)
            copied.append(new_msg)
        self.session.commit()
        return copied

    def spawn_twins_for_fork(
        self,
        conversation: Conversation,
        experiment_run_id: int,
        fork_turn: int,
        max_twins: int | None = None,
        include_control_replicate: bool = True,
    ) -> list[Twin]:
        twins = []

        control = self.create_twin(
            conversation_id=conversation.id,
            experiment_run_id=experiment_run_id,
            fork_turn=fork_turn,
            twin_type=TwinType.CONTROL,
            label="control_a",
            temperature=0.7,
            top_p=1.0,
            system_prompt_name="baseline",
        )
        self.copy_history_to_twin(conversation.id, control)
        twins.append(control)

        if include_control_replicate:
            replicate = self.create_twin(
                conversation_id=conversation.id,
                experiment_run_id=experiment_run_id,
                fork_turn=fork_turn,
                twin_type=TwinType.CONTROL_REPLICATE,
                label="control_b",
                temperature=0.7,
                top_p=1.0,
                system_prompt_name="baseline",
                parent_twin_id=control.id,
            )
            self.copy_history_to_twin(conversation.id, replicate)
            twins.append(replicate)
            if max_twins and len(twins) >= max_twins:
                return twins

        for prompt_name in ["simple", "medium", "complex"]:
            twin = self.create_twin(
                conversation_id=conversation.id,
                experiment_run_id=experiment_run_id,
                fork_turn=fork_turn,
                twin_type=TwinType.PROMPT,
                label=f"prompt_{prompt_name}",
                temperature=0.7,
                top_p=1.0,
                system_prompt_name=prompt_name,
            )
            self.copy_history_to_twin(conversation.id, twin)
            twins.append(twin)

        for combo in PARAM_COMBINATIONS:
            twin = self.create_twin(
                conversation_id=conversation.id,
                experiment_run_id=experiment_run_id,
                fork_turn=fork_turn,
                twin_type=TwinType.PARAMETER,
                label=f"param_{combo['label']}",
                temperature=combo["temperature"],
                top_p=combo["top_p"],
                system_prompt_name="baseline",
            )
            self.copy_history_to_twin(conversation.id, twin)
            twins.append(twin)
            if max_twins and len(twins) >= max_twins:
                return twins

        return twins

    def get_twin_messages(self, twin_id: int) -> list[Message]:
        query = (
            select(Message)
            .where(Message.twin_id == twin_id)
            .order_by(Message.turn_number)
        )
        return list(self.session.exec(query).all())
