from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table
from sqlmodel import select

from src.config import EXPORTS_DIR, settings
from src.database import get_session, init_db
from src.metrics.judge_parse import parse_judge_content
from src.models.entities import Conversation, ExperimentRun, MetricResult, Twin, TwinType
from src.services.experiment import run_experiment_from_config
from src.services.fork import ForkService
from src.services.mock_data import seed_mock_experiment

app = typer.Typer(help="CLI do TCC Digital Twins")
console = Console()


@app.command("run-experiment")
def run_experiment(
    config: str = typer.Argument(..., help="Caminho para poc_config.yaml"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Executa versão reduzida"),
    start_replication: int = typer.Option(
        1, "--start-replication", min=1, help="Réplica inicial (ex.: 2 para continuar)"
    ),
) -> None:
    init_db()
    if not settings.openai_api_key:
        console.print("[red]OPENAI_API_KEY não configurada.[/red]")
        console.print("Copie .env.example para .env e adicione sua chave.")
        raise typer.Exit(1)
    console.print(f"[bold]Iniciando experimento:[/bold] {config}")
    if dry_run:
        console.print("[yellow]Modo dry-run: 1 conversa, 1 fork, 3 twins (A + B + 1 perturbado)[/yellow]")
    elif start_replication > 1:
        console.print(f"[cyan]Continuando da réplica {start_replication}[/cyan]")

    try:
        with Path(config).open(encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        replications = 1 if dry_run else cfg.get("experiment", {}).get("replications", 1)

        experiment_id = run_experiment_from_config(
            config,
            dry_run=dry_run,
            start_replication=start_replication,
        )
        with get_session() as session:
            result = session.get(ExperimentRun, experiment_id)
        console.print(f"[green]Experimento concluído![/green] ID: {experiment_id}")
        if replications > 1:
            console.print(f"[cyan]Replicações executadas:[/cyan] {replications} (último ID: {experiment_id})")
        if result:
            console.print(f"Status: {result.status}")
            console.print(f"Replicação: {result.replication_index}")
            console.print(f"API calls: {result.total_api_calls}")
            console.print(f"Tokens: {result.total_tokens}")
            console.print(f"Custo estimado: ${result.estimated_cost_usd:.4f}")
    except Exception as exc:
        console.print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command("backfill-judge-scores")
def backfill_judge_scores(
    experiment_id: Optional[int] = typer.Option(None, help="ID do experimento (todos se omitido)"),
) -> None:
    """Recupera scores do judge salvos apenas no campo details (ex.: JSON em markdown)."""
    init_db()
    updated = 0

    with get_session() as session:
        query = select(MetricResult)
        if experiment_id is not None:
            query = query.where(MetricResult.experiment_run_id == experiment_id)

        for metric in session.exec(query).all():
            if metric.score is not None:
                continue
            score, justification = parse_judge_content(metric.details)
            if score is None:
                continue
            metric.score = score
            metric.value = str(score)
            if justification:
                metric.details = justification
            session.add(metric)
            updated += 1

        session.commit()

    console.print(f"[green]Scores recuperados:[/green] {updated}")


@app.command("export-results")
def export_results(
    experiment_id: Optional[int] = typer.Option(None, help="ID do experimento (último se omitido)"),
) -> None:
    init_db()
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with get_session() as session:
        if experiment_id is None:
            run = session.exec(
                select(ExperimentRun).order_by(ExperimentRun.id.desc())
            ).first()
        else:
            run = session.get(ExperimentRun, experiment_id)

        if not run:
            console.print("[red]Nenhum experimento encontrado[/red]")
            raise typer.Exit(1)

        twins = list(
            session.exec(select(Twin).where(Twin.experiment_run_id == run.id)).all()
        )

        rows = []
        for twin in twins:
            metrics = list(
                session.exec(select(MetricResult).where(MetricResult.twin_id == twin.id)).all()
            )
            row = {
                "experiment_id": run.id,
                "replication_index": run.replication_index,
                "twin_id": twin.id,
                "conversation_id": twin.conversation_id,
                "twin_type": twin.twin_type.value,
                "label": twin.label,
                "fork_turn": twin.fork_turn,
                "temperature": twin.temperature,
                "top_p": twin.top_p,
                "system_prompt_name": twin.system_prompt_name,
                "resolved": twin.resolved,
                "stopped_reason": twin.stopped_reason,
                "total_turns": twin.total_turns,
                "total_tokens": twin.total_tokens,
            }
            for m in metrics:
                score = m.score
                details = m.details
                if score is None:
                    recovered, justification = parse_judge_content(details)
                    if recovered is not None:
                        score = recovered
                        if justification:
                            details = justification
                row[f"metric_{m.metric_name}"] = score if score is not None else m.value
                row[f"metric_{m.metric_name}_details"] = details
            rows.append(row)

        csv_path = EXPORTS_DIR / f"results_exp_{run.id}.csv"
        json_path = EXPORTS_DIR / f"summary_exp_{run.id}.json"

        if rows:
            import pandas as pd

            df = pd.DataFrame(rows)
            df.to_csv(csv_path, index=False)

        summary = {
            "experiment_id": run.id,
            "name": run.name,
            "status": run.status,
            "dry_run": run.dry_run,
            "total_twins": len(twins),
            "total_api_calls": run.total_api_calls,
            "total_tokens": run.total_tokens,
            "estimated_cost_usd": run.estimated_cost_usd,
            "twins_by_type": {},
        }
        for twin in twins:
            t = twin.twin_type.value
            summary["twins_by_type"][t] = summary["twins_by_type"].get(t, 0) + 1

        json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

        console.print(f"[green]Exportado:[/green] {csv_path}")
        console.print(f"[green]Exportado:[/green] {json_path}")


@app.command("export-human-review")
def export_human_review(
    experiment_id: Optional[int] = typer.Option(None, help="ID do experimento (último se omitido)"),
    sample_rate: float = typer.Option(0.10, "--sample-rate", help="Fração de twins para revisão humana"),
    all_replications: bool = typer.Option(
        False, "--all-replications", help="Amostra de todas as replicações do mesmo experimento"
    ),
) -> None:
    """Exporta amostra para avaliação humana (última troca user/assistant + colunas em branco)."""
    init_db()
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with get_session() as session:
        experiment_ids: list[int] = []
        if experiment_id is not None:
            latest = session.get(ExperimentRun, experiment_id)
        else:
            latest = session.exec(
                select(ExperimentRun).order_by(ExperimentRun.id.desc())
            ).first()
        if not latest:
            console.print("[red]Nenhum experimento encontrado[/red]")
            raise typer.Exit(1)

        if all_replications:
            base_name = re.sub(r"_rep\d+$", "", latest.name)
            runs = session.exec(
                select(ExperimentRun).where(ExperimentRun.name.like(f"{base_name}%"))
            ).all()
            experiment_ids = sorted(
                {
                    run.id
                    for run in runs
                    if run.status == "completed" and not run.dry_run
                }
            )
        else:
            experiment_ids = [latest.id]

        fork_service = ForkService(session)
        candidates: list[dict] = []

        for exp_id in experiment_ids:
            run = session.get(ExperimentRun, exp_id)
            twins = list(
                session.exec(select(Twin).where(Twin.experiment_run_id == exp_id)).all()
            )
            for twin in twins:
                if twin.twin_type not in (TwinType.PROMPT, TwinType.PARAMETER):
                    continue
                conversation = session.get(Conversation, twin.conversation_id)
                if not conversation:
                    continue
                messages = fork_service.get_twin_messages(twin.id)
                last_user = next((m for m in reversed(messages) if m.role.value == "user"), None)
                last_assistant = next(
                    (m for m in reversed(messages) if m.role.value == "assistant"), None
                )
                if not last_user or not last_assistant:
                    continue

                control_a = session.exec(
                    select(Twin).where(
                        Twin.experiment_run_id == exp_id,
                        Twin.conversation_id == conversation.id,
                        Twin.fork_turn == twin.fork_turn,
                        Twin.twin_type == TwinType.CONTROL,
                    )
                ).first()
                baseline = ""
                if control_a:
                    control_msgs = fork_service.get_twin_messages(control_a.id)
                    baseline_msg = next(
                        (m for m in reversed(control_msgs) if m.role.value == "assistant"), None
                    )
                    baseline = baseline_msg.content if baseline_msg else ""

                candidates.append({
                    "experiment_id": exp_id,
                    "replication_index": run.replication_index if run else 1,
                    "twin_id": twin.id,
                    "conversation_external_id": conversation.external_id,
                    "conversation_title": conversation.title,
                    "category": conversation.category.value,
                    "difficulty": conversation.difficulty,
                    "constraints": conversation.constraints,
                    "twin_type": twin.twin_type.value,
                    "label": twin.label,
                    "fork_turn": twin.fork_turn,
                    "user_message": last_user.content,
                    "assistant_message": last_assistant.content,
                    "baseline_assistant_message": baseline,
                    "human_factualidade_1_5": "",
                    "human_robustez_1_5": "",
                    "human_aderencia_restricoes_1_5": "",
                    "human_notas": "",
                })

        if not candidates:
            console.print("[red]Nenhum twin candidato para revisão humana[/red]")
            raise typer.Exit(1)

        sample_size = max(1, round(len(candidates) * sample_rate))
        random.shuffle(candidates)
        sample = candidates[:sample_size]

        import pandas as pd

        label = "all" if all_replications and len(experiment_ids) > 1 else str(experiment_ids[-1])
        csv_path = EXPORTS_DIR / f"human_review_sample_{label}.csv"
        pd.DataFrame(sample).to_csv(csv_path, index=False)
        console.print(f"[green]Amostra humana exportada:[/green] {csv_path}")
        console.print(f"Total candidatos: {len(candidates)} | Amostra: {len(sample)} ({sample_rate:.0%})")


@app.command("seed-mock")
def seed_mock() -> None:
    """Popula banco com dados sintéticos para testar export/análise sem API."""
    init_db()
    with get_session() as session:
        result = seed_mock_experiment(session)
        experiment_id = result.id
    console.print(f"[green]Mock experiment criado![/green] ID: {experiment_id}")
    console.print("Twins: 72 (4 conversas × 2 forks × 9 twins, com control_b)")


@app.command("list-experiments")
def list_experiments() -> None:
    init_db()
    with get_session() as session:
        runs = session.exec(select(ExperimentRun).order_by(ExperimentRun.id)).all()

    table = Table(title="Experimentos")
    table.add_column("ID")
    table.add_column("Nome")
    table.add_column("Status")
    table.add_column("Rep")
    table.add_column("Dry Run")
    table.add_column("Custo USD")

    for run in runs:
        table.add_row(
            str(run.id),
            run.name,
            run.status,
            str(run.replication_index),
            str(run.dry_run),
            f"${run.estimated_cost_usd:.4f}" if run.estimated_cost_usd else "-",
        )
    console.print(table)


if __name__ == "__main__":
    app()
