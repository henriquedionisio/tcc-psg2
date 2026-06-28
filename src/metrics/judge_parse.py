from __future__ import annotations

import json
import re


def strip_markdown_json(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_judge_content(content: str | None) -> tuple[float | None, str | None]:
    """Extrai score e justificativa de respostas do judge (JSON puro ou ```json)."""
    if not content:
        return None, None

    text = str(content).strip()
    if text in {"skipped", ""}:
        return None, None
    if "Sem baseline para comparação" in text:
        return None, None
    if "Métrica aplicável apenas" in text:
        return None, None

    stripped = strip_markdown_json(text)
    try:
        data = json.loads(stripped)
        score = float(data["score"])
        justification = str(data.get("justification", stripped))
        return score, justification
    except (json.JSONDecodeError, TypeError, ValueError, KeyError):
        match = re.search(r'"score"\s*:\s*(\d+(?:\.\d+)?)', text)
        if match:
            return float(match.group(1)), text
        return None, text
