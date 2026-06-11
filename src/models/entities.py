from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class TwinType(str, Enum):
    CONTROL = "control"
    PROMPT = "prompt"
    PARAMETER = "parameter"


class ConversationCategory(str, Enum):
    FACTUAL = "factual"
    CREATIVE = "creative"
    INSTRUCTIONAL = "instructional"
    CONTEXTUAL = "contextual"


class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: str = Field(index=True, unique=True)
    category: ConversationCategory
    title: str
    objective: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    messages: List["Message"] = Relationship(back_populates="conversation")
    twins: List["Twin"] = Relationship(back_populates="conversation")


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id", index=True)
    twin_id: Optional[int] = Field(default=None, foreign_key="twin.id", index=True)
    role: MessageRole
    content: str
    turn_number: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    conversation: Optional["Conversation"] = Relationship(back_populates="messages")
    twin: Optional["Twin"] = Relationship(back_populates="messages")


class Twin(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id", index=True)
    experiment_run_id: Optional[int] = Field(default=None, foreign_key="experimentrun.id")
    parent_twin_id: Optional[int] = Field(default=None, foreign_key="twin.id")
    twin_type: TwinType
    label: str
    fork_turn: int
    temperature: float = 0.7
    top_p: float = 1.0
    system_prompt_name: str = "baseline"
    system_prompt: str = ""
    resolved: bool = False
    total_turns: int = 0
    total_tokens: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    conversation: Optional["Conversation"] = Relationship(back_populates="twins")
    messages: List["Message"] = Relationship(back_populates="twin")
    metric_results: List["MetricResult"] = Relationship(back_populates="twin")


class ExperimentRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    config_path: str
    dry_run: bool = False
    status: str = "pending"
    total_api_calls: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    twins: List["Twin"] = Relationship()
    metric_results: List["MetricResult"] = Relationship(back_populates="experiment_run")


class MetricResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    twin_id: int = Field(foreign_key="twin.id", index=True)
    experiment_run_id: Optional[int] = Field(default=None, foreign_key="experimentrun.id")
    metric_name: str
    score: Optional[float] = None
    value: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    twin: Optional["Twin"] = Relationship(back_populates="metric_results")
    experiment_run: Optional["ExperimentRun"] = Relationship(back_populates="metric_results")
