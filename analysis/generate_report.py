#!/usr/bin/env python3
"""Gera gráficos comparativos a partir dos exports do experimento."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "data" / ".matplotlib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.metrics.judge_parse import parse_judge_content

EXPORTS_DIR = ROOT / "data" / "exports"
CHARTS_DIR = EXPORTS_DIR / "charts"

PARAM_LABEL_ORDER = [
    "param_deterministic",
    "param_baseline_params",
    "param_high_temp_restricted",
    "param_max_variability",
]


def find_latest_csv() -> Optional[Path]:
    files = sorted(EXPORTS_DIR.glob("results_exp_*.csv"))
    return files[-1] if files else None


def _numeric_column(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def resolve_judge_column(df: pd.DataFrame, metric_col: str) -> pd.Series:
    """Usa score numérico ou recupera do campo *_details (ex.: ```json)."""
    scores = _numeric_column(df, metric_col).copy()
    details_col = f"{metric_col}_details"
    if details_col not in df.columns:
        return scores

    for idx in df.index:
        if pd.notna(scores.at[idx]):
            continue
        raw = df.at[idx, details_col]
        if pd.isna(raw):
            continue
        parsed, _ = parse_judge_content(str(raw))
        if parsed is not None:
            scores.at[idx] = parsed
    return scores


def _ordered_param_means(param_df: pd.DataFrame, value_col: str) -> pd.Series:
    means = param_df.groupby("label")[value_col].mean()
    ordered_labels = [label for label in PARAM_LABEL_ORDER if label in means.index]
    extra = [label for label in means.index if label not in ordered_labels]
    return means.reindex(ordered_labels + extra)


def generate_charts(df: pd.DataFrame, experiment_id: int) -> List[Path]:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    saved = []

    if "total_tokens" in df.columns and "twin_type" in df.columns:
        fig, ax = plt.subplots(figsize=(8, 5))
        df.groupby("twin_type")["total_tokens"].mean().plot(kind="bar", ax=ax, color="steelblue")
        ax.set_title("Tokens médios por tipo de twin")
        ax.set_ylabel("Tokens")
        ax.set_xlabel("Tipo de twin")
        path = CHARTS_DIR / f"tokens_by_type_exp_{experiment_id}.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        saved.append(path)

    prompt_df = df[df["twin_type"] == "prompt"].copy()
    if not prompt_df.empty:
        prompt_df["metric_factualidade"] = resolve_judge_column(prompt_df, "metric_factualidade")
        if prompt_df["metric_factualidade"].notna().any():
            fig, ax = plt.subplots(figsize=(8, 5))
            prompt_df.groupby("system_prompt_name")["metric_factualidade"].mean().plot(
                kind="bar", ax=ax, color="seagreen"
            )
            ax.set_title("Factualidade média por nível de prompt")
            ax.set_ylabel("Score (1-5)")
            ax.set_xlabel("Nível de prompt")
            path = CHARTS_DIR / f"factualidade_by_prompt_exp_{experiment_id}.png"
            fig.tight_layout()
            fig.savefig(path, dpi=150)
            plt.close(fig)
            saved.append(path)

    param_df = df[df["twin_type"] == "parameter"].copy()
    if not param_df.empty:
        param_df["metric_robustez"] = resolve_judge_column(param_df, "metric_robustez")
        if param_df["metric_robustez"].notna().any():
            fig, ax = plt.subplots(figsize=(10, 5))
            _ordered_param_means(param_df, "metric_robustez").plot(kind="bar", ax=ax, color="coral")
            ax.set_title("Robustez média por combinação de parâmetros")
            ax.set_ylabel("Score (1-5)")
            ax.set_xlabel("Combinação")
            plt.xticks(rotation=45, ha="right")
            path = CHARTS_DIR / f"robustez_by_params_exp_{experiment_id}.png"
            fig.tight_layout()
            fig.savefig(path, dpi=150)
            plt.close(fig)
            saved.append(path)

    if "fork_turn" in df.columns:
        robustez_df = df.copy()
        robustez_df["metric_robustez"] = resolve_judge_column(robustez_df, "metric_robustez")
        if robustez_df["metric_robustez"].notna().any():
            fig, ax = plt.subplots(figsize=(8, 5))
            robustez_df.groupby("fork_turn")["metric_robustez"].mean().plot(
                kind="bar", ax=ax, color="mediumpurple"
            )
            ax.set_title("Robustez média por turno do fork")
            ax.set_ylabel("Score (1-5)")
            ax.set_xlabel("Turno do fork")
            path = CHARTS_DIR / f"robustez_by_fork_turn_exp_{experiment_id}.png"
            fig.tight_layout()
            fig.savefig(path, dpi=150)
            plt.close(fig)
            saved.append(path)

    perturbation_df = df[df["twin_type"].isin(["prompt", "parameter"])].copy()
    if not perturbation_df.empty and "metric_attributed_divergence_pct" in perturbation_df.columns:
        perturbation_df["metric_attributed_divergence_pct"] = resolve_judge_column(
            perturbation_df, "metric_attributed_divergence_pct"
        )
        if perturbation_df["metric_attributed_divergence_pct"].notna().any():
            fig, ax = plt.subplots(figsize=(8, 5))
            perturbation_df.groupby("twin_type")["metric_attributed_divergence_pct"].mean().plot(
                kind="bar", ax=ax, color="teal"
            )
            ax.set_title("Divergência atribuível média por tipo de twin")
            ax.set_ylabel("Divergência atribuível (%)")
            ax.set_xlabel("Tipo de twin")
            path = CHARTS_DIR / f"attributed_divergence_by_type_exp_{experiment_id}.png"
            fig.tight_layout()
            fig.savefig(path, dpi=150)
            plt.close(fig)
            saved.append(path)

    replicate_df = df[df["twin_type"] == "control_replicate"].copy()
    if not replicate_df.empty and "metric_intrinsic_divergence_pct" in replicate_df.columns:
        replicate_df["metric_intrinsic_divergence_pct"] = resolve_judge_column(
            replicate_df, "metric_intrinsic_divergence_pct"
        )
        if replicate_df["metric_intrinsic_divergence_pct"].notna().any():
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.bar(
                ["Ruído intrínseco A/B"],
                [replicate_df["metric_intrinsic_divergence_pct"].mean()],
                color="slategray",
            )
            ax.set_title("Ruído intrínseco médio (controle A vs. réplica B)")
            ax.set_ylabel("Divergência (%)")
            path = CHARTS_DIR / f"intrinsic_divergence_exp_{experiment_id}.png"
            fig.tight_layout()
            fig.savefig(path, dpi=150)
            plt.close(fig)
            saved.append(path)

    if "resolved" in df.columns and "twin_type" in df.columns:
        resolved_df = df.copy()
        resolved_df["resolved"] = resolved_df["resolved"].map(
            {True: 1, False: 0, "True": 1, "False": 0}
        )
        resolved_df["resolved"] = pd.to_numeric(resolved_df["resolved"], errors="coerce")
        fig, ax = plt.subplots(figsize=(8, 5))
        resolved_df.groupby("twin_type")["resolved"].mean().plot(kind="bar", ax=ax, color="goldenrod")
        ax.set_title("Taxa de resolução por tipo de twin")
        ax.set_ylabel("Taxa de resolução")
        ax.set_xlabel("Tipo de twin")
        path = CHARTS_DIR / f"resolution_by_type_exp_{experiment_id}.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        saved.append(path)

    return saved


def main() -> None:
    csv_path = find_latest_csv()
    if not csv_path:
        print("Nenhum arquivo de resultados encontrado em data/exports/")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    experiment_id = int(csv_path.stem.split("_")[-1])
    charts = generate_charts(df, experiment_id)

    summary_path = EXPORTS_DIR / f"summary_exp_{experiment_id}.json"
    report = {
        "experiment_id": experiment_id,
        "total_twins": len(df),
        "charts_generated": [str(p) for p in charts],
    }
    if summary_path.exists():
        with summary_path.open(encoding="utf-8") as f:
            report["experiment_summary"] = json.load(f)

    report_path = EXPORTS_DIR / f"report_exp_{experiment_id}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Relatório gerado: {report_path}")
    for chart in charts:
        print(f"  Gráfico: {chart}")


if __name__ == "__main__":
    main()
