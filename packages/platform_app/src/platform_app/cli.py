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
    pipeline: str = typer.Argument(help="Pipeline to run: ars, txn, txn_v4, ics, ics_append"),
    data_file: Path = typer.Argument(help="Primary data file path"),
    odd_file: Path | None = typer.Option(None, "--odd", help="ODD file (for txn_v4, ars)"),
    tran_file: Path | None = typer.Option(None, "--tran", help="Transaction file (for txn)"),
    output_dir: Path = typer.Option("output", "--output", "-o", help="Output directory"),
    client_id: str = typer.Option("", "--client-id", help="Client identifier"),
    client_name: str = typer.Option("", "--client-name", help="Client display name"),
) -> None:
    """Run a single analysis pipeline."""
    from platform_app.orchestrator import run_pipeline

    input_files = _build_input_files(pipeline, data_file, odd_file, tran_file)

    def _echo_progress(msg: str) -> None:
        typer.echo(msg)

    typer.echo(f"Running {pipeline} pipeline...")
    results = run_pipeline(
        pipeline,
        input_files=input_files,
        output_dir=output_dir,
        client_id=client_id,
        client_name=client_name,
        progress_callback=_echo_progress,
    )
    typer.echo(f"Complete: {len(results)} analyses produced.")
    typer.echo(f"Output: {output_dir}/")


@app.command()
def run_all(
    data_dir: Path = typer.Argument(help="Directory containing client data files"),
    output_dir: Path = typer.Option("output", "--output", "-o", help="Output directory"),
    client_id: str = typer.Option("", "--client-id", help="Client identifier"),
    client_name: str = typer.Option("", "--client-name", help="Client display name"),
    pipelines: str = typer.Option("auto", "--pipelines", help="Comma-separated pipelines or 'auto'"),
) -> None:
    """Run all applicable pipelines for a client's data directory."""
    from platform_app.orchestrator import run_all as orchestrator_run_all

    input_files = _scan_data_dir(data_dir)
    if not input_files:
        typer.echo(f"No recognized data files found in {data_dir}", err=True)
        raise typer.Exit(code=1)

    pipeline_list = None if pipelines == "auto" else pipelines.split(",")

    def _echo_progress(msg: str) -> None:
        typer.echo(msg)

    typer.echo(f"Detected files: {', '.join(f'{k}={v.name}' for k, v in input_files.items())}")
    all_results = orchestrator_run_all(
        input_files=input_files,
        output_dir=output_dir,
        client_id=client_id,
        client_name=client_name,
        pipelines=pipeline_list,
        progress_callback=_echo_progress,
    )

    total = sum(len(r) for r in all_results.values())
    typer.echo(f"Complete: {len(all_results)} pipelines, {total} total analyses.")


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


def _build_input_files(
    pipeline: str, data_file: Path, odd_file: Path | None, tran_file: Path | None,
) -> dict[str, Path]:
    """Map CLI args to input_files dict based on pipeline type."""
    files: dict[str, Path] = {}
    if pipeline == "ars":
        files["oddd"] = data_file
    elif pipeline in ("txn", "txn_v4"):
        files["tran"] = tran_file or data_file
        if odd_file:
            files["odd"] = odd_file
    elif pipeline == "ics":
        files["ics"] = data_file
    elif pipeline == "ics_append":
        files["base_dir"] = data_file
    return files


def _scan_data_dir(data_dir: Path) -> dict[str, Path]:
    """Scan a directory and auto-detect file roles by naming convention."""
    files: dict[str, Path] = {}
    for f in sorted(data_dir.iterdir()):
        if not f.is_file():
            continue
        name = f.stem.lower()
        suffix = f.suffix.lower()
        if suffix not in (".csv", ".xlsx", ".xls"):
            continue
        if "oddd" in name:
            files["oddd"] = f
        elif "odd" in name and "oddd" not in name:
            files["odd"] = f
        elif "tran" in name:
            files["tran"] = f
        elif "ics" in name:
            files["ics"] = f
    return files


if __name__ == "__main__":
    app()
