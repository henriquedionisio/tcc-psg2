from __future__ import annotations

from src.models.entities import ConversationCategory, Message, MessageRole
from src.services.llm import LLMService, load_prompt


class UserSimulator:
    def __init__(self, llm: LLMService) -> None:
        self.llm = llm
        self.template = load_prompt("user_simulator.txt")

    def generate_user_message(
        self,
        objective: str,
        category: ConversationCategory,
        history: list[Message],
    ) -> str:
        system_prompt = self.template.format(
            objective=objective,
            category=category.value,
        )
        messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in history
            if msg.role != MessageRole.SYSTEM
        ]
        response = self.llm.chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7,
            top_p=1.0,
            max_tokens=200,
        )
        return response.content.strip()

    def is_conversation_resolved(self, message: str) -> bool:
        lower = message.lower()
        resolution_signals = [
            "obrigado",
            "resolve minha dúvida",
            "resolveu",
            "perfeito",
            "é isso",
            "era isso",
            "muito obrigado",
            "thanks",
        ]
        return any(signal in lower for signal in resolution_signals)
