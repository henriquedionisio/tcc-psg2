#!/usr/bin/env python3
"""Gera gráficos da monografia (v2 agregado, avaliação humana, arquitetura)."""

from __future__ import annotations

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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd

from analysis.chart_utils import (
    CATEGORY_LABELS,
    CHARTS_DIR,
    EXPORTS_DIR,
    PARAM_LABEL_ORDER,
    ROTEIRO_B_ORDER,
    category_for_conversation_id,
    conversation_id_map,
    load_conversation_metadata,
)
from analysis.generate_report import generate_charts, resolve_judge_column

V2_CSV = EXPORTS_DIR / "results_poc_v2_all_replications.csv"
HUMAN_CSV = EXPORTS_DIR / "human_review_sample_all.csv"
V2_SUFFIX = "poc_v2_all"


def _ordered_param_means(param_df: pd.DataFrame, value_col: str) -> pd.Series:
    means = param_df.groupby("label")[value_col].mean()
    ordered = [label for label in PARAM_LABEL_ORDER if label in means.index]
    extra = [label for label in means.index if label not in ordered]
    return means.reindex(ordered + extra)


def _save_fig(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def generate_v2_aggregated_charts(df: pd.DataFrame) -> List[Path]:
    """Equivalente aos gráficos por experimento, agregando as cinco réplicas v2."""
    saved: List[Path] = []

    if "total_tokens" in df.columns and "twin_type" in df.columns:
        fig, ax = plt.subplots(figsize=(8, 5))
        df.groupby("twin_type")["total_tokens"].mean().plot(kind="bar", ax=ax, color="steelblue")
        ax.set_title("Tokens médios por tipo de gêmeo (v2, 720 gêmeos)")
        ax.set_ylabel("Tokens")
        ax.set_xlabel("Tipo de gêmeo")
        saved.append(_save_fig(fig, CHARTS_DIR / f"tokens_by_type_{V2_SUFFIX}.png"))

    prompt_df = df[df["twin_type"] == "prompt"].copy()
    if not prompt_df.empty:
        prompt_df["metric_factualidade"] = resolve_judge_column(prompt_df, "metric_factualidade")
        if prompt_df["metric_factualidade"].notna().any():
            fig, ax = plt.subplots(figsize=(8, 5))
            prompt_df.groupby("system_prompt_name")["metric_factualidade"].mean().plot(
                kind="bar", ax=ax, color="seagreen"
            )
            ax.set_title("Factualidade média por nível de prompt (v2)")
            ax.set_ylabel("Score (1–5)")
            ax.set_xlabel("Nível de prompt")
            saved.append(_save_fig(fig, CHARTS_DIR / f"factualidade_by_prompt_{V2_SUFFIX}.png"))

    param_df = df[df["twin_type"] == "parameter"].copy()
    if not param_df.empty:
        param_df["metric_robustez"] = resolve_judge_column(param_df, "metric_robustez")
        if param_df["metric_robustez"].notna().any():
            fig, ax = plt.subplots(figsize=(10, 5))
            _ordered_param_means(param_df, "metric_robustez").plot(kind="bar", ax=ax, color="coral")
            ax.set_title("Robustez média por combinação de parâmetros (v2)")
            ax.set_ylabel("Score (1–5)")
            ax.set_xlabel("Combinação")
            plt.xticks(rotation=45, ha="right")
            saved.append(_save_fig(fig, CHARTS_DIR / f"robustez_by_params_{V2_SUFFIX}.png"))

    if "fork_turn" in df.columns:
        robustez_df = df.copy()
        robustez_df["metric_robustez"] = resolve_judge_column(robustez_df, "metric_robustez")
        if robustez_df["metric_robustez"].notna().any():
            fig, ax = plt.subplots(figsize=(8, 5))
            robustez_df.groupby("fork_turn")["metric_robustez"].mean().plot(
                kind="bar", ax=ax, color="mediumpurple"
            )
            ax.set_title("Robustez média por turno do ponto de cópia (v2)")
            ax.set_ylabel("Score (1–5)")
            ax.set_xlabel("Turno do fork")
            saved.append(_save_fig(fig, CHARTS_DIR / f"robustez_by_fork_turn_{V2_SUFFIX}.png"))

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
            ax.set_title("Divergência atribuível média por tipo de gêmeo (v2)")
            ax.set_ylabel("Divergência atribuível (%)")
            ax.set_xlabel("Tipo de gêmeo")
            saved.append(_save_fig(fig, CHARTS_DIR / f"attributed_by_type_{V2_SUFFIX}.png"))

    replicate_df = df[df["twin_type"] == "control_replicate"].copy()
    if not replicate_df.empty and "metric_intrinsic_divergence_pct" in replicate_df.columns:
        replicate_df["metric_intrinsic_divergence_pct"] = resolve_judge_column(
            replicate_df, "metric_intrinsic_divergence_pct"
        )
        if replicate_df["metric_intrinsic_divergence_pct"].notna().any():
            fig, ax = plt.subplots(figsize=(9, 5))
            by_rep = replicate_df.groupby("replication_index")["metric_intrinsic_divergence_pct"].mean()
            by_rep.plot(kind="bar", ax=ax, color="slategray")
            ax.set_title("Variação natural por execução (referência vs. réplica idêntica)")
            ax.set_ylabel("Divergência intrínseca (%)")
            ax.set_xlabel("Execução (réplica)")
            saved.append(_save_fig(fig, CHARTS_DIR / "intrinsic_by_replication_poc_v2.png"))

    if "resolved" in df.columns and "twin_type" in df.columns:
        resolved_df = df.copy()
        resolved_df["resolved"] = resolved_df["resolved"].map(
            {True: 1, False: 0, "True": 1, "False": 0}
        )
        resolved_df["resolved"] = pd.to_numeric(resolved_df["resolved"], errors="coerce")
        fig, ax = plt.subplots(figsize=(8, 5))
        resolved_df.groupby("twin_type")["resolved"].mean().plot(kind="bar", ax=ax, color="goldenrod")
        ax.set_title("Taxa de resolução por tipo de gêmeo (v2)")
        ax.set_ylabel("Taxa de resolução")
        ax.set_xlabel("Tipo de gêmeo")
        saved.append(_save_fig(fig, CHARTS_DIR / f"resolution_by_type_{V2_SUFFIX}.png"))

    return saved


def _human_judge_pairs(human_df: pd.DataFrame, v2_df: pd.DataFrame) -> pd.DataFrame:
    judge_cols = ["twin_id", "metric_factualidade", "metric_robustez"]
    merged = human_df.merge(v2_df[judge_cols], on="twin_id", how="left")
    merged["metric_factualidade"] = resolve_judge_column(merged, "metric_factualidade")
    merged["metric_robustez"] = resolve_judge_column(merged, "metric_robustez")
    return merged


def _scatter_human_vs_judge(
    pairs: pd.DataFrame,
    human_col: str,
    judge_col: str,
    title: str,
    path: Path,
) -> Optional[Path]:
    data = pairs[[human_col, judge_col]].dropna()
    if data.empty:
        return None

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(data[judge_col], data[human_col], alpha=0.75, color="steelblue", edgecolors="white")
    lo, hi = 0.5, 5.5
    ax.plot([lo, hi], [lo, hi], "--", color="gray", linewidth=1, label="Concordância perfeita")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("Avaliador automático (1–5)")
    ax.set_ylabel("Avaliador humano (1–5)")
    ax.set_title(title)
    ax.set_aspect("equal")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)

    human_mean = data[human_col].mean()
    judge_mean = data[judge_col].mean()
    ax.text(
        0.05,
        0.95,
        f"n = {len(data)}\nHumano: {human_mean:.2f}\nAutomático: {judge_mean:.2f}",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )
    return _save_fig(fig, path)


def generate_human_review_charts() -> List[Path]:
    if not HUMAN_CSV.exists():
        print(f"Aviso: {HUMAN_CSV} não encontrado")
        return []

    human_df = pd.read_csv(HUMAN_CSV)
    for col in ["human_factualidade_1_5", "human_robustez_1_5", "human_aderencia_restricoes_1_5"]:
        if col in human_df.columns:
            human_df[col] = pd.to_numeric(human_df[col], errors="coerce")

    saved: List[Path] = []

    if V2_CSV.exists():
        v2_df = pd.read_csv(V2_CSV)
        pairs = _human_judge_pairs(human_df, v2_df)

        p = _scatter_human_vs_judge(
            pairs,
            "human_factualidade_1_5",
            "metric_factualidade",
            "Factualidade: humano vs. avaliador automático",
            CHARTS_DIR / "human_vs_judge_factualidade.png",
        )
        if p:
            saved.append(p)

        p = _scatter_human_vs_judge(
            pairs,
            "human_robustez_1_5",
            "metric_robustez",
            "Robustez: humano vs. avaliador automático",
            CHARTS_DIR / "human_vs_judge_robustez.png",
        )
        if p:
            saved.append(p)

    aderencia_df = human_df[
        human_df["conversation_external_id"].isin(ROTEIRO_B_ORDER)
        & human_df["human_aderencia_restricoes_1_5"].notna()
    ]
    if not aderencia_df.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        means = (
            aderencia_df.groupby("conversation_external_id")["human_aderencia_restricoes_1_5"]
            .mean()
            .reindex(ROTEIRO_B_ORDER)
        )
        means.plot(kind="bar", ax=ax, color="darkorange")
        ax.set_title("Aderência às regras por roteiro com restrições (C1B–C4B)")
        ax.set_ylabel("Score humano (1–5)")
        ax.set_xlabel("Roteiro")
        ax.set_ylim(0, 5.5)
        for i, val in enumerate(means):
            if pd.notna(val):
                ax.text(i, val + 0.08, f"{val:.2f}", ha="center", fontsize=9)
        saved.append(_save_fig(fig, CHARTS_DIR / "aderencia_regras_por_roteiro_b.png"))

    return saved


def generate_results_by_category_chart(df: pd.DataFrame) -> Optional[Path]:
    id_map = conversation_id_map()
    work = df.copy()
    work["category"] = work["conversation_id"].apply(
        lambda cid: category_for_conversation_id(cid, id_map)
    )
    work = work[work["category"].notna()]
    if work.empty:
        return None

    work["metric_factualidade"] = resolve_judge_column(work, "metric_factualidade")
    work["metric_robustez"] = resolve_judge_column(work, "metric_robustez")
    work["resolved_num"] = work["resolved"].map({True: 1, False: 0, "True": 1, "False": 0})
    work["resolved_num"] = pd.to_numeric(work["resolved_num"], errors="coerce")

    categories = ["factual", "creative", "instructional", "contextual"]
    labels = [CATEGORY_LABELS[c] for c in categories]
    resolution = work.groupby("category")["resolved_num"].mean().reindex(categories)
    factualidade = work.groupby("category")["metric_factualidade"].mean().reindex(categories)
    robustez = work.groupby("category")["metric_robustez"].mean().reindex(categories)

    x = np.arange(len(categories))
    width = 0.25
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width, resolution * 100, width, label="Resolução (%)", color="goldenrod")
    ax.bar(x, factualidade, width, label="Factualidade (1–5)", color="seagreen")
    ax.bar(x + width, robustez, width, label="Robustez (1–5)", color="coral")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Valor médio")
    ax.set_title("Indicadores médios por tipo de conversa (v2)")
    ax.legend(loc="upper right")
    ax.set_ylim(0, 105)
    return _save_fig(fig, CHARTS_DIR / "results_by_conversation_type_poc_v2.png")


def generate_architecture_diagram() -> Path:
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.axis("off")

    boxes = [
        (0.3, 1.2, 2.0, 1.6, "Roteiro\n(início fixo +\nrestrições)", "#E8F4FD"),
        (2.8, 1.2, 2.0, 1.6, "Motor de\ncópia\n(turno N)", "#FFF3E0"),
        (5.3, 0.4, 2.4, 3.2, "Gêmeos paralelos\n• Referência\n• Réplica controle\n• Prompt (3 níveis)\n• Parâmetros (4)", "#E8F5E9"),
        (8.2, 1.2, 1.6, 1.6, "Simulador\nde usuário", "#F3E5F5"),
        (10.2, 0.6, 1.5, 2.8, "Métricas\n• Tokens/turnos\n• Resolução\n• Judge LLM\n• Divergência", "#FCE4EC"),
    ]

    for x, y, w, h, text, color in boxes:
        rect = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.05,rounding_size=0.1",
            linewidth=1.5,
            edgecolor="#333333",
            facecolor=color,
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9, wrap=True)

    arrows = [
        (2.3, 2.0, 2.8, 2.0),
        (4.8, 2.0, 5.3, 2.0),
        (7.7, 2.0, 8.2, 2.0),
        (9.8, 2.0, 10.2, 2.0),
    ]
    for x1, y1, x2, y2 in arrows:
        ax.add_patch(
            FancyArrowPatch(
                (x1, y1),
                (x2, y2),
                arrowstyle="-|>",
                mutation_scale=15,
                linewidth=1.5,
                color="#444444",
            )
        )

    ax.set_title("Pipeline de Digital Twins conversacionais", fontsize=12, pad=12)
    return _save_fig(fig, CHARTS_DIR / "architecture_pipeline.png")


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    all_saved: List[Path] = []

    if V2_CSV.exists():
        v2_df = pd.read_csv(V2_CSV)
        all_saved.extend(generate_v2_aggregated_charts(v2_df))
        p = generate_results_by_category_chart(v2_df)
        if p:
            all_saved.append(p)
    else:
        print(f"Aviso: {V2_CSV} não encontrado")

    all_saved.extend(generate_human_review_charts())
    all_saved.append(generate_architecture_diagram())

    # Piloto v1 (exp 3) — referência no texto
    v1_csv = EXPORTS_DIR / "results_exp_3.csv"
    if v1_csv.exists():
        v1_df = pd.read_csv(v1_csv)
        all_saved.extend(generate_charts(v1_df, 3))

    print(f"Gráficos gerados: {len(all_saved)}")
    for path in all_saved:
        print(f"  {path}")


if __name__ == "__main__":
    main()
