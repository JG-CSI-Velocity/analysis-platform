"""Typer CLI for txn_analysis."""

from __future__ import annotations

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler

from txn_analysis.pipeline import export_outputs, run_pipeline
from txn_analysis.settings import Settings

app = typer.Typer(help="Credit union debit card transaction analysis.")
console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@app.command()
def analyze(
    data_file: Path = typer.Argument(..., help="Path to CSV/Excel data file."),
    config: Path = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
    output_dir: Path = typer.Option(None, "--output-dir", "-o", help="Output directory"),
    client_id: str = typer.Option(None, "--client-id", help="Client identifier"),
    client_name: str = typer.Option(None, "--client-name", help="Client display name"),
    top_n: int = typer.Option(50, "--top-n", help="Number of top results"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """Run the full analysis pipeline."""
    _setup_logging(verbose)

    overrides = {
        "data_file": data_file,
        "top_n": top_n,
    }
    if output_dir:
        overrides["output_dir"] = output_dir
    if client_id:
        overrides["client_id"] = client_id
    if client_name:
        overrides["client_name"] = client_name

    if config and config.exists():
        settings = Settings.from_yaml(config, **overrides)
    else:
        settings = Settings.from_args(**overrides)

    def on_progress(step: int, total: int, msg: str) -> None:
        console.print(f"  [{step + 1}/{total}] {msg}")

    console.print(f"[bold]Transaction Analysis[/bold] -- {data_file.name}")
    result = run_pipeline(settings, on_progress=on_progress)

    successful = sum(1 for a in result.analyses if a.error is None)
    console.print(f"  {successful}/{len(result.analyses)} analyses completed")
    console.print(f"  {len(result.charts)} charts generated")

    files = export_outputs(result)
    for f in files:
        console.print(f"  Output: {f}")

    console.print("[bold green]Done.[/bold green]")
