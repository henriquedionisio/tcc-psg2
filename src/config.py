from __future__ import annotations

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT_DIR / "prompts"
DATA_DIR = ROOT_DIR / "data"
EXPORTS_DIR = DATA_DIR / "exports"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_judge_model: str = "gpt-4o-mini"
    database_url: str = f"sqlite:///{DATA_DIR / 'tcc.db'}"
    max_budget_usd: float = 10.0

    # Cost estimates per 1M tokens (gpt-4o-mini)
    input_cost_per_1m: float = 0.15
    output_cost_per_1m: float = 0.60


settings = Settings()
