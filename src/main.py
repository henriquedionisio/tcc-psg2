from __future__ import annotations

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from src.database import get_session, init_db
from src.models.entities import Conversation, ConversationCategory, Message, MessageRole, Twin
from src.services.fork import ForkService

app = FastAPI(
    title="TCC Digital Twins API",
    description="API para fork controlado de conversas e avaliação de variabilidade em LLMs",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


class CreateConversationRequest(BaseModel):
    external_id: str
    category: str
    title: str
    objective: str


class AddMessageRequest(BaseModel):
    role: str
    content: str
    turn_number: int


class ForkRequest(BaseModel):
    fork_turn: int
    experiment_run_id: int = 1


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/conversations")
def create_conversation(req: CreateConversationRequest) -> dict:
    with get_session() as session:
        conv = Conversation(
            external_id=req.external_id,
            category=ConversationCategory(req.category),
            title=req.title,
            objective=req.objective,
        )
        session.add(conv)
        session.commit()
        session.refresh(conv)
        return {"id": conv.id, "external_id": conv.external_id}


@app.get("/conversations")
def list_conversations() -> list[dict]:
    with get_session() as session:
        convs = session.exec(select(Conversation)).all()
        return [
            {
                "id": c.id,
                "external_id": c.external_id,
                "category": c.category.value,
                "title": c.title,
                "objective": c.objective,
            }
            for c in convs
        ]


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int) -> dict:
    with get_session() as session:
        conv = session.get(Conversation, conversation_id)
        if not conv:
            raise HTTPException(404, "Conversa não encontrada")
        messages = session.exec(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.twin_id.is_(None))
            .order_by(Message.turn_number)
        ).all()
        return {
            "id": conv.id,
            "external_id": conv.external_id,
            "category": conv.category,
            "title": conv.title,
            "objective": conv.objective,
            "messages": [
                {"role": m.role, "content": m.content, "turn": m.turn_number}
                for m in messages
            ],
        }


@app.post("/conversations/{conversation_id}/messages")
def add_message(conversation_id: int, req: AddMessageRequest) -> dict:
    with get_session() as session:
        conv = session.get(Conversation, conversation_id)
        if not conv:
            raise HTTPException(404, "Conversa não encontrada")
        msg = Message(
            conversation_id=conversation_id,
            role=MessageRole(req.role),
            content=req.content,
            turn_number=req.turn_number,
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)
        return {"id": msg.id, "turn": msg.turn_number}


@app.post("/conversations/{conversation_id}/fork")
def fork_conversation(conversation_id: int, req: ForkRequest) -> dict:
    with get_session() as session:
        conv = session.get(Conversation, conversation_id)
        if not conv:
            raise HTTPException(404, "Conversa não encontrada")
        fork_service = ForkService(session)
        twins = fork_service.spawn_twins_for_fork(conv, req.experiment_run_id, req.fork_turn)
        return {
            "conversation_id": conversation_id,
            "fork_turn": req.fork_turn,
            "twins": [
                {
                    "id": t.id,
                    "label": t.label,
                    "type": t.twin_type,
                    "temperature": t.temperature,
                    "top_p": t.top_p,
                    "system_prompt_name": t.system_prompt_name,
                }
                for t in twins
            ],
        }


@app.get("/twins/{twin_id}")
def get_twin(twin_id: int) -> dict:
    with get_session() as session:
        twin = session.get(Twin, twin_id)
        if not twin:
            raise HTTPException(404, "Twin não encontrado")
        messages = session.exec(
            select(Message).where(Message.twin_id == twin_id).order_by(Message.turn_number)
        ).all()
        return {
            "id": twin.id,
            "label": twin.label,
            "type": twin.twin_type,
            "fork_turn": twin.fork_turn,
            "resolved": twin.resolved,
            "total_turns": twin.total_turns,
            "total_tokens": twin.total_tokens,
            "messages": [
                {"role": m.role, "content": m.content, "turn": m.turn_number}
                for m in messages
            ],
        }
