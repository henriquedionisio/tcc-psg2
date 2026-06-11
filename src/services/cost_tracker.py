from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.config import EXPORTS_DIR, settings

COST_LOG_PATH = Path(settings.database_url.replace("sqlite:///", "")).parent / "cost_log.json"


class CostTracker:
    def __init__(self) -> None:
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.api_calls = 0
        COST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def record(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.api_calls += 1
        self._persist()

    @property
    def estimated_cost_usd(self) -> float:
        input_cost = (self.total_prompt_tokens / 1_000_000) * settings.input_cost_per_1m
        output_cost = (self.total_completion_tokens / 1_000_000) * settings.output_cost_per_1m
        return input_cost + output_cost

    @property
    def total_tokens(self) -> int:
        return self.total_prompt_tokens + self.total_completion_tokens

    def check_budget(self) -> None:
        if self.estimated_cost_usd >= settings.max_budget_usd:
            raise RuntimeError(
                f"Orçamento excedido: ${self.estimated_cost_usd:.4f} >= ${settings.max_budget_usd:.2f}"
            )

    def _persist(self) -> None:
        data = {
            "updated_at": datetime.utcnow().isoformat(),
            "api_calls": self.api_calls,
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "max_budget_usd": settings.max_budget_usd,
        }
        COST_LOG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def summary(self) -> dict:
        return {
            "api_calls": self.api_calls,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
        }
