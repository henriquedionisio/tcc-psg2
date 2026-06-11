from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from sqlmodel import select

from src.config import EXPORTS_DIR, settings
from src.database import get_session, init_db
from src.models.entities import ExperimentRun, MetricResult, Twin
from src.services.experiment import run_experiment_from_config
from src.services.mock_data import seed_mock_experiment

app = typer.Typer(help="CLI do TCC Digital Twins")
console = Console()


@app.command("run-experiment")
def run_experiment(
    config: str = typer.Argument(..., help="Caminho para poc_config.yaml"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Executa versão reduzida"),
) -> None:
    init_db()
    if not settings.openai_api_key:
        console.print("[red]OPENAI_API_KEY não configurada.[/red]")
        console.print("Copie .env.example para .env e adicione sua chave.")
        raise typer.Exit(1)
    console.print(f"[bold]Iniciando experimento:[/bold] {config}")
    if dry_run:
        console.print("[yellow]Modo dry-run: 1 conversa, 1 fork, 2 twins[/yellow]")

    try:
        experiment_id = run_experiment_from_config(config, dry_run=dry_run)
        with get_session() as session:
            result = session.get(ExperimentRun, experiment_id)
        console.print(f"[green]Experimento concluído![/green] ID: {experiment_id}")
        if result:
            console.print(f"Status: {result.status}")
            console.print(f"API calls: {result.total_api_calls}")
            console.print(f"Tokens: {result.total_tokens}")
            console.print(f"Custo estimado: ${result.estimated_cost_usd:.4f}")
    except Exception as exc:
        console.print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(1) from exc


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
                "twin_id": twin.id,
                "conversation_id": twin.conversation_id,
                "twin_type": twin.twin_type.value,
                "label": twin.label,
                "fork_turn": twin.fork_turn,
                "temperature": twin.temperature,
                "top_p": twin.top_p,
                "system_prompt_name": twin.system_prompt_name,
                "resolved": twin.resolved,
                "total_turns": twin.total_turns,
                "total_tokens": twin.total_tokens,
            }
            for m in metrics:
                row[f"metric_{m.metric_name}"] = m.score if m.score is not None else m.value
                row[f"metric_{m.metric_name}_details"] = m.details
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


@app.command("seed-mock")
def seed_mock() -> None:
    """Popula banco com dados sintéticos para testar export/análise sem API."""
    init_db()
    with get_session() as session:
        result = seed_mock_experiment(session)
        experiment_id = result.id
    console.print(f"[green]Mock experiment criado![/green] ID: {experiment_id}")
    console.print(f"Twins: 64 (4 conversas × 2 forks × 8 twins)")


@app.command("list-experiments")
def list_experiments() -> None:
    init_db()
    with get_session() as session:
        runs = session.exec(select(ExperimentRun).order_by(ExperimentRun.id)).all()

    table = Table(title="Experimentos")
    table.add_column("ID")
    table.add_column("Nome")
    table.add_column("Status")
    table.add_column("Dry Run")
    table.add_column("Custo USD")

    for run in runs:
        table.add_row(
            str(run.id),
            run.name,
            run.status,
            str(run.dry_run),
            f"${run.estimated_cost_usd:.4f}" if run.estimated_cost_usd else "-",
        )
    console.print(table)


if __name__ == "__main__":
    app()
