"""Typer CLI for the unified analysis platform."""

from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(
    name="analysis-platform",
    help="Unified banking analysis platform: ARS, Transaction, and ICS pipelines.",
)


@app.command()
def run(
    pipeline: str = typer.Argument(help="Pipeline to run: ars, txn, ics, or all"),
    client: str = typer.Argument(help="Client name or 'all' for batch"),
    oddd_path: Path | None = typer.Option(None, "--oddd", help="Path to ODDD file"),
    tran_path: Path | None = typer.Option(None, "--tran", help="Path to transaction file"),
    odd_path: Path | None = typer.Option(None, "--odd", help="Path to ODD file"),
    output_dir: Path = typer.Option("output", "--output", help="Output directory"),
    config: Path = typer.Option("config/platform.yaml", "--config", help="Config file path"),
) -> None:
    """Run analysis pipeline(s) for a client."""
    typer.echo(f"Running {pipeline} for {client}...")
    # TODO: Wire up orchestrator (Phase 6)
    raise typer.Exit(code=1)


@app.command()
def batch(
    manifest: Path = typer.Argument(help="YAML/CSV manifest of clients + file paths"),
    pipelines: str = typer.Option("all", "--pipelines", help="Comma-separated pipeline names"),
    workers: int = typer.Option(4, "--workers", help="Parallel workers (1=sequential)"),
) -> None:
    """Run batch analysis across multiple clients."""
    typer.echo(f"Batch processing from {manifest}...")
    # TODO: Wire up batch orchestrator (Phase 6)
    raise typer.Exit(code=1)


@app.command()
def format_oddd(
    input_path: Path = typer.Argument(help="Path to raw ODDD file"),
    output_path: Path | None = typer.Option(
        None, "--output", help="Output path (default: *-formatted.xlsx)"
    ),
) -> None:
    """Run ODDD formatting pipeline (standalone)."""
    from shared.data_loader import load_oddd

    typer.echo(f"Formatting {input_path}...")
    df = load_oddd(input_path, format_data=True)

    if output_path is None:
        output_path = input_path.with_stem(f"{input_path.stem}-formatted")
        if output_path.suffix != ".xlsx":
            output_path = output_path.with_suffix(".xlsx")

    df.to_excel(str(output_path), index=False)
    typer.echo(f"Saved formatted file: {output_path} ({len(df)} rows, {len(df.columns)} columns)")


if __name__ == "__main__":
    app()
