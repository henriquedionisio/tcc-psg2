"""Utilitários compartilhados para geração de gráficos da monografia."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "data" / ".matplotlib"))

EXPORTS_DIR = ROOT / "data" / "exports"
CHARTS_DIR = EXPORTS_DIR / "charts"
CONVERSATIONS_DIR = ROOT / "experiments" / "conversations"

PARAM_LABEL_ORDER = [
    "param_deterministic",
    "param_baseline_params",
    "param_high_temp_restricted",
    "param_max_variability",
]

CATEGORY_LABELS = {
    "factual": "Factual",
    "creative": "Criativo",
    "instructional": "Instrucional",
    "contextual": "Contextual",
}

ROTEIRO_B_ORDER = ["C1B", "C2B", "C3B", "C4B"]


def load_conversation_metadata() -> Dict[str, dict]:
    """Carrega external_id -> {category, title} a partir dos YAML de roteiro."""
    meta: Dict[str, dict] = {}
    for path in sorted(CONVERSATIONS_DIR.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        external_id = data.get("id")
        if external_id:
            meta[external_id] = {
                "category": data.get("category"),
                "title": data.get("title"),
            }
    return meta


def conversation_id_map() -> Dict[int, str]:
    """Mapeia conversation_id do banco para external_id (C1, C2, ...)."""
    try:
        from sqlmodel import Session, select

        from src.database import engine
        from src.models.entities import Conversation

        with Session(engine) as session:
            convs = session.exec(select(Conversation)).all()
            if convs:
                return {c.id: c.external_id for c in convs}
    except Exception:
        pass

    meta = load_conversation_metadata()
    return {idx: external_id for idx, external_id in enumerate(meta.keys(), start=1)}


def category_for_conversation_id(conv_id: int, id_map: Optional[Dict[int, str]] = None) -> Optional[str]:
    id_map = id_map or conversation_id_map()
    external_id = id_map.get(int(conv_id))
    if not external_id:
        return None
    meta = load_conversation_metadata()
    return meta.get(external_id, {}).get("category")
