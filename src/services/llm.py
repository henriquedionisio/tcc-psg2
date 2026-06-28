from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx
from openai import OpenAI

from src.config import PROMPTS_DIR, settings
from src.services.cost_tracker import CostTracker


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt não encontrado: {path}")
    return path.read_text(encoding="utf-8").strip()


MAX_MESSAGE_CHARS = 1200
DEFAULT_MAX_HISTORY_MESSAGES = 10


class LLMService:
    def __init__(self, cost_tracker: CostTracker | None = None) -> None:
        self.cost_tracker = cost_tracker or CostTracker()
        self._http_client: httpx.Client | None = None
        self._client: OpenAI | None = None
        self._reset_client()

    def _reset_client(self) -> None:
        if self._http_client is not None:
            self._http_client.close()
        self._http_client = httpx.Client(timeout=120.0, trust_env=False)
        self._client = OpenAI(
            api_key=settings.openai_api_key,
            http_client=self._http_client,
        )

    @staticmethod
    def trim_messages(
        messages: list[dict[str, str]],
        max_messages: int = DEFAULT_MAX_HISTORY_MESSAGES,
        max_chars: int = MAX_MESSAGE_CHARS,
    ) -> list[dict[str, str]]:
        window = messages[-max_messages:] if max_messages > 0 else messages
        return [
            {"role": msg["role"], "content": msg["content"][:max_chars]}
            for msg in window
        ]

    @staticmethod
    def truncate_text(text: str, max_chars: int = MAX_MESSAGE_CHARS) -> str:
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."

    def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str = "",
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: int = 500,
        model: str | None = None,
        max_history_messages: int = DEFAULT_MAX_HISTORY_MESSAGES,
    ) -> LLMResponse:
        self.cost_tracker.check_budget()
        messages = self.trim_messages(messages, max_messages=max_history_messages)
        api_messages: list[dict[str, str]] = []
        if system_prompt:
            api_messages.append(
                {"role": "system", "content": self.truncate_text(system_prompt)}
            )
        for msg in messages:
            if msg["role"] in ("user", "assistant"):
                api_messages.append({"role": msg["role"], "content": msg["content"]})

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self._client.chat.completions.create(
                    model=model or settings.openai_model,
                    messages=api_messages,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )
                break
            except Exception as exc:
                last_error = exc
                if "431" in str(exc) and attempt < 2:
                    self._reset_client()
                    continue
                raise
        else:
            assert last_error is not None
            raise last_error

        content = response.choices[0].message.content or ""
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else prompt_tokens + completion_tokens

        self.cost_tracker.record(prompt_tokens, completion_tokens)

        return LLMResponse(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    def judge(
        self,
        prompt_template: str,
        variables: dict[str, str],
        model: str | None = None,
    ) -> LLMResponse:
        prompt = prompt_template
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{key}}}", self.truncate_text(str(value)))
        return self.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            top_p=1.0,
            max_tokens=300,
            model=model or settings.openai_judge_model,
        )
