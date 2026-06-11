from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class MetricContext:
    twin_id: int
    twin_label: str
    twin_type: str
    objective: str
    category: str
    fork_turn: int
    user_message: str
    assistant_message: str
    baseline_message: str | None = None
    total_turns: int = 0
    total_tokens: int = 0


@dataclass
class EvaluatedMetric:
    metric_name: str
    score: float | None = None
    value: str | None = None
    details: str | None = None


class BaseMetric(ABC):
    name: str

    @abstractmethod
    def evaluate(self, context: MetricContext) -> EvaluatedMetric:
        pass
