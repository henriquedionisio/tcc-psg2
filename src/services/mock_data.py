from __future__ import annotations

"""Gera dados sintéticos para validar pipeline de export/análise sem chamadas à API."""

import random
from datetime import datetime

from sqlmodel import Session

from src.models.entities import (
    Conversation,
    ConversationCategory,
    ExperimentRun,
    Message,
    MessageRole,
    MetricResult,
    Twin,
    TwinType,
)
from src.services.fork import PARAM_COMBINATIONS


def seed_mock_experiment(session: Session) -> ExperimentRun:
    experiment = ExperimentRun(
        name="poc_mock_v1",
        config_path="experiments/poc_config.yaml",
        dry_run=False,
        status="completed",
        total_api_calls=128,
        total_tokens=45000,
        estimated_cost_usd=0.035,
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    session.add(experiment)
    session.commit()
    session.refresh(experiment)

    conversations_data = [
        ("C1", ConversationCategory.FACTUAL, "Ciclo da água", "Explicar ciclo da água"),
        ("C2", ConversationCategory.CREATIVE, "Conto sci-fi", "Conto em 3 atos"),
        ("C3", ConversationCategory.INSTRUCTIONAL, "Plano Python", "Plano 4 semanas"),
        ("C4", ConversationCategory.CONTEXTUAL, "Matrícula USP", "Info institucional"),
    ]

    fork_turns = [3, 6]
    twin_defs: list[dict] = [{"type": TwinType.CONTROL, "label": "control", "prompt": "baseline", "temp": 0.7, "top_p": 1.0}]
    for p in ["simple", "medium", "complex"]:
        twin_defs.append({"type": TwinType.PROMPT, "label": f"prompt_{p}", "prompt": p, "temp": 0.7, "top_p": 1.0})
    for combo in PARAM_COMBINATIONS:
        twin_defs.append({
            "type": TwinType.PARAMETER,
            "label": f"param_{combo['label']}",
            "prompt": "baseline",
            "temp": combo["temperature"],
            "top_p": combo["top_p"],
        })

    for ext_id, category, title, objective in conversations_data:
        conv = Conversation(
            external_id=ext_id,
            category=category,
            title=title,
            objective=objective,
        )
        session.add(conv)
        session.commit()
        session.refresh(conv)

        for turn in range(1, 4):
            session.add(Message(
                conversation_id=conv.id,
                role=MessageRole.USER if turn % 2 == 1 else MessageRole.ASSISTANT,
                content=f"Mensagem seed {turn} da conversa {ext_id}",
                turn_number=turn,
            ))
        session.commit()

        for fork_turn in fork_turns:
            for tdef in twin_defs:
                twin = Twin(
                    conversation_id=conv.id,
                    experiment_run_id=experiment.id,
                    twin_type=tdef["type"],
                    label=tdef["label"],
                    fork_turn=fork_turn,
                    temperature=tdef["temp"],
                    top_p=tdef["top_p"],
                    system_prompt_name=tdef["prompt"],
                    system_prompt=f"Prompt {tdef['prompt']}",
                    resolved=random.random() > 0.3,
                    total_turns=random.randint(2, 5),
                    total_tokens=random.randint(800, 3500),
                )
                session.add(twin)
                session.commit()
                session.refresh(twin)

                for turn in range(1, fork_turn + 3):
                    session.add(Message(
                        conversation_id=conv.id,
                        twin_id=twin.id,
                        role=MessageRole.USER if turn % 2 == 1 else MessageRole.ASSISTANT,
                        content=f"[{twin.label}] turn {turn}",
                        turn_number=turn,
                        total_tokens=random.randint(50, 200),
                    ))
                session.commit()

                base_fact = 3.5 if tdef["prompt"] == "complex" else 3.0
                if tdef["type"] == TwinType.PARAMETER and tdef["temp"] >= 1.0:
                    base_fact -= 0.5
                metrics = [
                    ("tokens", twin.total_tokens, str(twin.total_tokens)),
                    ("turns", twin.total_turns, str(twin.total_turns)),
                    ("resolution", 1.0 if twin.resolved else 0.0, "resolved" if twin.resolved else "unresolved"),
                    ("factualidade", round(base_fact + random.uniform(-0.5, 0.5), 2), None),
                    ("robustez", round(4.0 - abs(tdef["temp"] - 0.7) * 1.5 + random.uniform(-0.3, 0.3), 2), None),
                ]
                if category in (ConversationCategory.CONTEXTUAL, ConversationCategory.INSTRUCTIONAL):
                    metrics.append(("adequacao_institucional", round(3.8 + random.uniform(-0.5, 0.5), 2), None))

                for name, score, value in metrics:
                    session.add(MetricResult(
                        twin_id=twin.id,
                        experiment_run_id=experiment.id,
                        metric_name=name,
                        score=float(score) if score is not None else None,
                        value=value,
                        details=f"Mock metric for {name}",
                    ))
                session.commit()

    return experiment
