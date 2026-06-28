#!/usr/bin/env python3
"""Compara notas humanas (CSV) com scores do judge no banco."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from sqlmodel import Session, select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.database import engine
from src.models.entities import MetricResult

EXPORTS = ROOT / "data" / "exports"
CSV_PATH = EXPORTS / "human_review_sample_all.csv"
OUT_PATH = EXPORTS / "human_review_comparison.json"


def _load_judge_scores(twin_ids: list[int]) -> pd.DataFrame:
    rows: list[dict] = []
    with Session(engine) as session:
        for twin_id in twin_ids:
            metrics = session.exec(
                select(MetricResult).where(MetricResult.twin_id == twin_id)
            ).all()
            row = {"twin_id": twin_id}
            for m in metrics:
                if m.metric_name in ("factualidade", "robustez") and m.score is not None:
                    row[f"judge_{m.metric_name}"] = m.score
            rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    if not CSV_PATH.exists():
        print(f"Arquivo não encontrado: {CSV_PATH}")
        sys.exit(1)

    df = pd.read_csv(CSV_PATH)
    required = ["twin_id", "human_factualidade_1_5", "human_robustez_1_5"]
    for col in required:
        if col not in df.columns:
            print(f"Coluna ausente: {col}")
            sys.exit(1)

    for col in ["human_factualidade_1_5", "human_robustez_1_5", "human_aderencia_restricoes_1_5"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    filled = df["human_factualidade_1_5"].notna() & df["human_robustez_1_5"].notna()
    if not filled.any():
        print("Nenhuma linha preenchida ainda. Preencha human_factualidade_1_5 e human_robustez_1_5.")
        sys.exit(0)

    work = df[filled].copy()
    judge = _load_judge_scores(work["twin_id"].astype(int).tolist())
    merged = work.merge(judge, on="twin_id", how="left")

    report: dict = {
        "rows_filled": int(filled.sum()),
        "rows_total": len(df),
        "comparisons": {},
    }

    for human_col, judge_col in [
        ("human_factualidade_1_5", "judge_factualidade"),
        ("human_robustez_1_5", "judge_robustez"),
    ]:
        if judge_col not in merged.columns:
            continue
        pair = merged[[human_col, judge_col]].dropna()
        if pair.empty:
            report["comparisons"][human_col] = {"n": 0, "message": "Sem overlap com judge"}
            continue
        diff = pair[human_col] - pair[judge_col]
        report["comparisons"][human_col] = {
            "n": int(len(pair)),
            "human_mean": round(pair[human_col].mean(), 2),
            "judge_mean": round(pair[judge_col].mean(), 2),
            "mean_abs_diff": round(diff.abs().mean(), 2),
            "correlation": round(pair[human_col].corr(pair[judge_col]), 3)
            if len(pair) > 1
            else None,
        }

    aderencia = merged["human_aderencia_restricoes_1_5"].dropna()
    if not aderencia.empty:
        report["aderencia_restricoes"] = {
            "n": int(len(aderencia)),
            "mean": round(aderencia.mean(), 2),
        }

    OUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Comparação salva: {OUT_PATH}")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
