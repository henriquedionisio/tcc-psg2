from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

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


class LLMService:
    def __init__(self, cost_tracker: CostTracker | None = None) -> None:
        self.cost_tracker = cost_tracker or CostTracker()

    def _client(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: int = 500,
    ) -> ChatOpenAI:
        return ChatOpenAI(
            model=model or settings.openai_model,
            temperature=temperature,
            model_kwargs={"top_p": top_p},
            max_tokens=max_tokens,
            api_key=settings.openai_api_key,
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str = "",
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: int = 500,
        model: str | None = None,
    ) -> LLMResponse:
        self.cost_tracker.check_budget()
        lc_messages = []
        if system_prompt:
            lc_messages.append(SystemMessage(content=system_prompt))
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

        client = self._client(model=model, temperature=temperature, top_p=top_p, max_tokens=max_tokens)
        response = client.invoke(lc_messages)

        usage = response.response_metadata.get("token_usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

        self.cost_tracker.record(prompt_tokens, completion_tokens)

        return LLMResponse(
            content=response.content,
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
            prompt = prompt.replace(f"{{{key}}}", value)
        return self.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            top_p=1.0,
            max_tokens=300,
            model=model or settings.openai_judge_model,
        )
