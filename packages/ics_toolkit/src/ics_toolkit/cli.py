"""Unified Typer CLI for ICS Toolkit."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer

from ics_toolkit.exceptions import ICSToolkitError
from ics_toolkit.settings import DEFAULT_CONFIG_PATH

app = typer.Typer(
    name="ics-toolkit",
    help="ICS data pipeline: append accounts and generate analytics reports.",
    no_args_is_help=True,
)

append_app = typer.Typer(
    name="append",
    help="Data preparation: organize, merge, match ICS accounts.",
    no_args_is_help=True,
)
app.add_typer(append_app, name="append")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s" if not verbose else "%(levelname)-8s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def _load_settings(
    config: Path | None = None,
    **overrides,
):
    """Build Settings from CLI options + YAML."""
    from ics_toolkit.settings import Settings

    config_path = config or DEFAULT_CONFIG_PATH
    filtered = {k: v for k, v in overrides.items() if v is not None}
    return Settings.from_yaml(config_path=config_path, **filtered)


# ---------------------------------------------------------------------------
# Append subcommands
# ---------------------------------------------------------------------------


@append_app.callback()
def append_callback(
    ctx: typer.Context,
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
    base_dir: Path | None = typer.Option(None, "--base-dir", "-d", help="Base ICS directory"),
    ars_dir: Path | None = typer.Option(None, "--ars-dir", help="ARS directory with ODD files"),
    dry_run: bool | None = typer.Option(None, "--dry-run", "-n", help="Preview without changes"),
    match_month: str | None = typer.Option(None, "--match-month", "-m", help="Month (YYYY.MM)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug logging"),
) -> None:
    """ICS Append -- organize, merge, match."""
    _setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["base_dir"] = base_dir
    ctx.obj["ars_dir"] = ars_dir
    ctx.obj["dry_run"] = dry_run
    ctx.obj["match_month"] = match_month


def _build_append_settings(ctx: typer.Context):
    """Build AppendSettings from context."""
    from ics_toolkit.settings import AppendSettings

    overrides: dict = {}
    for key in ("base_dir", "ars_dir", "dry_run", "match_month"):
        val = ctx.obj.get(key)
        if val is not None:
            overrides[key] = val
    return AppendSettings(**overrides)


@append_app.command()
def organize(ctx: typer.Context) -> None:
    """Organize loose files into client folders."""
    from ics_toolkit.append.pipeline import run_organize

    settings = _build_append_settings(ctx)
    moved = run_organize(settings)
    total = sum(len(v) for v in moved.values())
    typer.echo(f"Organized {total} files into {len(moved)} folders")


@append_app.command()
def merge(
    ctx: typer.Context,
    client: str | None = typer.Option(None, "--client", help="Single client ID"),
) -> None:
    """Merge REF+DM files per client."""
    from ics_toolkit.append.pipeline import run_merge

    settings = _build_append_settings(ctx)
    client_ids = [client] if client else None
    results = run_merge(settings, client_ids=client_ids)
    for r in results:
        typer.echo(f"{r.client_id}: REF={r.ref_count} DM={r.dm_count} Total={r.total}")


@append_app.command()
def match(
    ctx: typer.Context,
    client: str | None = typer.Option(None, "--client", help="Single client ID"),
) -> None:
    """Match ICS accounts against ODD files."""
    from ics_toolkit.append.pipeline import run_match

    settings = _build_append_settings(ctx)
    metadata = run_match(settings)
    for m in metadata:
        typer.echo(m.summary)


@append_app.command(name="run-all")
def append_run_all(ctx: typer.Context) -> None:
    """Execute full append pipeline: organize -> merge -> match."""
    from ics_toolkit.append.pipeline import run_pipeline

    settings = _build_append_settings(ctx)
    result = run_pipeline(settings)
    typer.echo(
        f"Pipeline complete: {len(result.merge_results)} merges, "
        f"{len(result.match_metadata)} matches"
    )
    if result.errors:
        for err in result.errors:
            typer.echo(f"ERROR: {err}", err=True)


# ---------------------------------------------------------------------------
# Analyze command
# ---------------------------------------------------------------------------


@app.command()
def analyze(
    data_file: Path = typer.Argument(
        None,
        help="Path to the client CSV/Excel file.",
        exists=False,
    ),
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH, "--config", "-c", help="Path to config.yaml file."
    ),
    output_dir: Path = typer.Option(None, "--output", "-o", help="Output directory for reports."),
    client_id: str = typer.Option(None, "--client-id", help="Client identifier."),
    client_name: str = typer.Option(None, "--client-name", help="Client name for report titles."),
    cohort_start: str = typer.Option(None, "--cohort-start", help="Cohort start month (YYYY-MM)."),
    ics_not_in_dump: int = typer.Option(
        None, "--ics-not-in-dump", help="Count of ICS accounts not in data dump."
    ),
    no_charts: bool = typer.Option(False, "--no-charts", help="Skip chart rendering (faster)."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Run ICS analysis and generate reports.

    Usage:
        python -m ics_toolkit analyze data/client_file.xlsx
        python -m ics_toolkit analyze --config config.yaml
    """
    _setup_logging(verbose)
    logger = logging.getLogger(__name__)

    try:
        overrides: dict = {"analysis": {}}
        if data_file is not None:
            overrides["analysis"]["data_file"] = data_file
        if output_dir is not None:
            overrides["analysis"]["output_dir"] = output_dir
        if client_id is not None:
            overrides["analysis"]["client_id"] = client_id
        if client_name is not None:
            overrides["analysis"]["client_name"] = client_name
        if cohort_start is not None:
            overrides["analysis"]["cohort_start"] = cohort_start
        if ics_not_in_dump is not None:
            overrides["analysis"]["ics_not_in_dump"] = ics_not_in_dump

        from ics_toolkit.settings import Settings

        settings = Settings.from_yaml(config_path=config, **overrides)
        analysis_settings = settings.analysis

        logger.info("Client: %s (%s)", analysis_settings.client_name, analysis_settings.client_id)
        logger.info("Data: %s", analysis_settings.data_file)
        logger.info("Output: %s", analysis_settings.output_dir)

        from ics_toolkit.analysis.pipeline import export_outputs, run_pipeline

        result = run_pipeline(analysis_settings, skip_charts=no_charts)

        successful = [a for a in result.analyses if a.error is None]
        logger.info("Analyses completed: %d/%d", len(successful), len(result.analyses))

        generated = export_outputs(result, skip_charts=no_charts)

        if generated:
            logger.info("")
            logger.info("Generated reports:")
            for path in generated:
                logger.info("  %s", path)
        else:
            logger.warning("No reports were generated.")

    except ICSToolkitError as e:
        logger.error(str(e))
        raise typer.Exit(code=1) from None
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(code=1) from None


@app.command(name="chart-catalog")
def chart_catalog(
    data_file: Path = typer.Argument(
        None,
        help="Path to the client CSV/Excel file.",
        exists=False,
    ),
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH, "--config", "-c", help="Path to config.yaml file."
    ),
    output_dir: Path = typer.Option(None, "--output", "-o", help="Output directory."),
    client_id: str = typer.Option(None, "--client-id", help="Client identifier."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Generate a chart catalog PPTX with one slide per chart and metadata labels.

    Each slide shows the chart image, section, function name, and source .py file.
    Use this to review charts one-by-one and provide feedback.

    Usage:
        python -m ics_toolkit chart-catalog data/client_file.xlsx
    """
    _setup_logging(verbose)
    logger = logging.getLogger(__name__)

    try:
        overrides: dict = {"analysis": {}}
        if data_file is not None:
            overrides["analysis"]["data_file"] = data_file
        if output_dir is not None:
            overrides["analysis"]["output_dir"] = output_dir
        if client_id is not None:
            overrides["analysis"]["client_id"] = client_id

        from ics_toolkit.settings import Settings

        settings = Settings.from_yaml(config_path=config, **overrides)
        analysis_settings = settings.analysis

        logger.info("Client: %s (%s)", analysis_settings.client_name, analysis_settings.client_id)
        logger.info("Data: %s", analysis_settings.data_file)

        from ics_toolkit.analysis.pipeline import run_pipeline

        result = run_pipeline(analysis_settings, skip_charts=False)

        successful = [a for a in result.analyses if a.error is None]
        logger.info(
            "Analyses: %d/%d  Charts: %d",
            len(successful),
            len(result.analyses),
            len(result.chart_pngs),
        )

        from ics_toolkit.analysis.exports.pptx import write_chart_catalog

        path = write_chart_catalog(
            analysis_settings,
            result.analyses,
            result.chart_pngs,
        )
        logger.info("")
        logger.info("Chart catalog: %s", path)

    except ICSToolkitError as e:
        logger.error(str(e))
        raise typer.Exit(code=1) from None
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
