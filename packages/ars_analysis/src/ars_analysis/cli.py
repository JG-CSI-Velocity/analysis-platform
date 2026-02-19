"""ARS Pipeline CLI -- Typer application with Rich output."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ars_analysis.exceptions import ARSError, ConfigError, DataError
from ars_analysis.logging_setup import setup_logging
from ars_analysis.pipeline.context import ClientInfo, OutputPaths, PipelineContext
from ars_analysis.pipeline.error_guidance import get_error_guidance
from ars_analysis.pipeline.runner import PipelineStep, StepResult, run_pipeline
from ars_analysis.pipeline.steps.analyze import step_analyze, step_analyze_selected
from ars_analysis.pipeline.steps.generate import step_archive, step_generate
from ars_analysis.pipeline.steps.load import step_load_file
from ars_analysis.pipeline.steps.subsets import step_subsets

console = Console()
app = typer.Typer(
    name="ars",
    help="ARS Automated Reporting System -- analysis pipeline for 300+ client reviews.",
    no_args_is_help=True,
)


def _setup(verbose: bool = False) -> None:
    """Common setup for all commands."""
    setup_logging(log_dir=Path("logs"), verbose=verbose)


def _load_settings():
    """Load ARSSettings from config files."""
    from ars_analysis.config import ARSSettings
    return ARSSettings()


def _show_config(settings, phase: str = "") -> None:
    """Print a summary of loaded config paths and CSM sources."""
    paths = settings.paths
    sources = settings.csm_sources.sources

    table = Table(title=f"Configuration{f' -- {phase}' if phase else ''}", show_lines=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_column("Status", justify="center")

    # Key paths with existence check
    for label, path in [
        ("ars_base", paths.ars_base),
        ("retrieve_dir (raw)", paths.retrieve_dir),
        ("watch_root (ready)", paths.watch_root),
        ("presentations_dir", paths.presentations_dir),
        ("log_dir", paths.log_dir),
        ("template_path", paths.template_path),
    ]:
        try:
            exists = path.exists()
        except OSError:
            exists = False
        status = "[green]OK[/green]" if exists else "[red]NOT FOUND[/red]"
        table.add_row(label, str(path), status)

    console.print(table)

    # CSM sources
    if sources:
        src_table = Table(title=f"CSM Sources ({len(sources)})", show_lines=False)
        src_table.add_column("CSM", style="cyan")
        src_table.add_column("Path")
        src_table.add_column("Status", justify="center")
        for name, src_path in sources.items():
            try:
                exists = src_path.exists()
            except OSError:
                exists = False
            status = "[green]OK[/green]" if exists else "[yellow]OFFLINE[/yellow]"
            src_table.add_row(name, str(src_path), status)
        console.print(src_table)

    console.print()


def _parse_modules(modules_str: str | None) -> list[str] | None:
    """Parse comma-separated module IDs. Returns None for 'all'."""
    if modules_str is None:
        return None
    return [m.strip() for m in modules_str.split(",") if m.strip()]


def _display_error(exc: Exception) -> None:
    """Show user-friendly error with guidance."""
    title, guidance = get_error_guidance(exc)
    console.print(Panel(
        f"[bold red]{title}[/bold red]\n\n{exc}\n\n[dim]{guidance}[/dim]",
        title="Error",
        border_style="red",
    ))


def _display_results(results: list[StepResult], json_output: bool = False) -> None:
    """Show pipeline results as table or JSON."""
    if json_output:
        data = [
            {"name": r.name, "success": r.success, "elapsed": round(r.elapsed_seconds, 2), "error": r.error}
            for r in results
        ]
        console.print_json(json.dumps({"steps": data}))
        return

    table = Table(title="Pipeline Results")
    table.add_column("Step", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Time", justify="right")
    table.add_column("Error", style="red")

    for r in results:
        status = "[green]OK[/green]" if r.success else "[red]FAIL[/red]"
        table.add_row(r.name, status, f"{r.elapsed_seconds:.1f}s", r.error or "")

    console.print(table)


# ---------------------------------------------------------------------------
# retrieve
# ---------------------------------------------------------------------------

@app.command()
def retrieve(
    month: str | None = typer.Option(None, help="Month to retrieve (YYYY.MM)"),
    limit: int = typer.Option(0, "--limit", "-l", help="Max files per CSM (0 = all)"),
    json_output: bool = typer.Option(False, "--json", help="Output structured JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """Retrieve ODD files from CSM source folders into the local directory."""
    _setup(verbose=verbose)

    try:
        settings = _load_settings()
    except Exception as exc:
        _display_error(exc)
        raise typer.Exit(1)

    if not json_output:
        console.print(f"Target month: [bold]{month or 'current'}[/bold]")
        if limit:
            console.print(f"Limit: [bold]{limit}[/bold] per CSM")

    from ars_analysis.pipeline.steps.retrieve import retrieve_all

    result = retrieve_all(settings, target_month=month, max_per_csm=limit)

    if json_output:
        console.print_json(json.dumps({
            "copied": len(result.copied),
            "skipped": len(result.skipped),
            "errors": len(result.errors),
            "details": {
                "copied": result.copied,
                "skipped": result.skipped,
                "errors": result.errors,
            },
        }))
        return

    table = Table(title="Retrieve Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right")
    table.add_row("Copied", f"[green]{len(result.copied)}[/green]")
    table.add_row("Skipped (already present)", f"[yellow]{len(result.skipped)}[/yellow]")
    table.add_row("Errors", f"[red]{len(result.errors)}[/red]")
    console.print(table)

    if result.copied:
        console.print("\n[bold]Copied files:[/bold]")
        for csm, fname in result.copied:
            console.print(f"  {csm}: {fname}")

    if result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for csm, fname, err in result.errors:
            console.print(f"  {csm}: {fname} -- {err}")


# ---------------------------------------------------------------------------
# format
# ---------------------------------------------------------------------------

@app.command()
def format(
    month: str | None = typer.Option(None, help="Month to format (YYYY.MM)"),
    limit: int = typer.Option(0, "--limit", help="Max files per CSM (0 = all)"),
    json_output: bool = typer.Option(False, "--json", help="Output structured JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """Format retrieved ODD files (6-step ARS formatting)."""
    _setup(verbose=verbose)

    try:
        settings = _load_settings()
    except Exception as exc:
        _display_error(exc)
        raise typer.Exit(1)

    if not json_output:
        console.print(f"Target month: [bold]{month or 'current'}[/bold]")
        if limit:
            console.print(f"Limit: [bold]{limit}[/bold] per CSM")
        console.print()

    from ars_analysis.pipeline.steps.format import format_all

    result = format_all(settings, target_month=month, max_per_csm=limit)

    if json_output:
        console.print_json(json.dumps({
            "formatted": len(result.formatted),
            "errors": len(result.errors),
            "details": {
                "formatted": result.formatted,
                "errors": result.errors,
            },
        }))
        return

    table = Table(title="Format Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right")
    table.add_row("Formatted", f"[green]{len(result.formatted)}[/green]")
    table.add_row("Errors", f"[red]{len(result.errors)}[/red]")
    console.print(table)

    if result.formatted:
        console.print("\n[bold]Formatted files:[/bold]")
        for csm, cid, fname in result.formatted:
            console.print(f"  {csm}/{cid}: {fname}")

    if result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for csm, fname, err in result.errors:
            console.print(f"  {csm}: {fname} -- {err}")


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------

@app.command()
def scan(
    month: str | None = typer.Option(None, help="Month to scan (YYYY.MM)"),
    csm: str | None = typer.Option(None, help="Filter by CSM name"),
    json_output: bool = typer.Option(False, "--json", help="Output structured JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """List clients with data ready for analysis."""
    _setup(verbose=verbose)

    try:
        settings = _load_settings()
    except Exception as exc:
        _display_error(exc)
        raise typer.Exit(1)

    from ars_analysis.pipeline.steps.scan import scan_ready_files

    files = scan_ready_files(settings, target_month=month, csm_filter=csm)

    if json_output:
        data = [
            {
                "client_id": f.client_id,
                "csm": f.csm_name,
                "filename": f.filename,
                "file_path": str(f.file_path),
                "month": f.month,
                "size_mb": f.file_size_mb,
                "is_formatted": f.is_formatted,
                "modified": f.modified_time.isoformat(),
            }
            for f in files
        ]
        console.print_json(json.dumps({"files": data, "count": len(data)}))
        return

    if not files:
        console.print("[yellow]No ready files found.[/yellow]")
        return

    table = Table(title=f"Ready Files ({len(files)})")
    table.add_column("Client ID", style="cyan")
    table.add_column("CSM")
    table.add_column("File")
    table.add_column("Size (MB)", justify="right")
    table.add_column("Formatted", justify="center")
    table.add_column("Modified")

    for f in files:
        fmt = "[green]Yes[/green]" if f.is_formatted else "[yellow]No[/yellow]"
        table.add_row(
            f.client_id, f.csm_name, f.filename,
            f"{f.file_size_mb:.1f}", fmt,
            f.modified_time.strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


# ---------------------------------------------------------------------------
# run (single client)
# ---------------------------------------------------------------------------

@app.command()
def run(
    file: str = typer.Argument(..., help="Path to formatted ODD file"),
    modules: str | None = typer.Option(
        None, help="Comma-separated module IDs (default: all registered)"
    ),
    config: str | None = typer.Option(None, help="Path to client config JSON"),
    output_dir: str | None = typer.Option(None, "--output-dir", help="Output directory override"),
    skip_pptx: bool = typer.Option(False, help="Skip PowerPoint generation"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
    json_output: bool = typer.Option(False, "--json", help="Output structured JSON"),
) -> None:
    """Analyze a single client and generate deliverables."""
    _setup(verbose=verbose)

    file_path = Path(file)
    if not file_path.exists():
        _display_error(FileNotFoundError(f"File not found: {file_path}"))
        raise typer.Exit(1)

    # Load analytics modules
    from ars_analysis.analytics.registry import load_all_modules
    try:
        load_all_modules()
    except ConfigError as exc:
        logger.warning("Some modules failed to load: {err}", err=exc)

    # Build context
    client_info = _load_client_info(config, file_path)
    out_base = Path(output_dir) if output_dir else file_path.parent
    paths = OutputPaths.from_base(out_base, client_info.client_id, client_info.month)

    ctx = PipelineContext(client=client_info, paths=paths)

    # Build step list based on --modules flag
    module_ids = _parse_modules(modules)
    if module_ids:
        analyze_step = PipelineStep(
            "run_analyses",
            lambda c, ids=module_ids: step_analyze_selected(c, ids),
        )
    else:
        analyze_step = PipelineStep("run_analyses", step_analyze)

    steps = [
        PipelineStep("load_data", lambda c: step_load_file(c, file_path)),
        PipelineStep("create_subsets", step_subsets),
        analyze_step,
        PipelineStep("generate_output", step_generate),
        PipelineStep("archive", step_archive, critical=False),
    ]

    try:
        results = run_pipeline(ctx, steps)
        _display_results(results, json_output)

        if all(r.success for r in results):
            if not json_output:
                console.print(f"\n[green]Analysis complete for {client_info.client_name}[/green]")
        else:
            raise typer.Exit(1)
    except ARSError as exc:
        _display_error(exc)
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# batch
# ---------------------------------------------------------------------------

@app.command()
def batch(
    month: str | None = typer.Option(None, help="Month to process (YYYY.MM)"),
    csm: str | None = typer.Option(None, help="Filter by CSM name"),
    modules: str | None = typer.Option(
        None, help="Comma-separated module IDs (default: all registered)"
    ),
    workers: int = typer.Option(1, "--workers", "-w", help="Parallel workers (1=sequential)"),
    local_temp: bool = typer.Option(False, "--local-temp", help="Copy to local temp before processing (faster on network drives)"),
    config: str | None = typer.Option(None, help="Path to config override"),
    json_output: bool = typer.Option(False, "--json", help="Output structured JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """Process all formatted clients for a month in batch."""
    _setup(verbose=verbose)

    from ars_analysis.analytics.registry import load_all_modules
    from ars_analysis.pipeline.batch import run_batch
    from ars_analysis.pipeline.steps.scan import scan_ready_files

    try:
        load_all_modules()
    except ConfigError as exc:
        logger.warning("Some modules failed to load: {err}", err=exc)

    try:
        settings = _load_settings()
    except Exception as exc:
        _display_error(exc)
        raise typer.Exit(1)

    # Use config defaults if CLI flags not explicitly set
    max_w = workers if workers > 1 else getattr(settings.pipeline, "max_workers", 1)
    use_temp = local_temp or getattr(settings.pipeline, "use_local_temp", False)

    if not json_output:
        console.print(f"Target month: [bold]{month or 'current'}[/bold]")
        if csm:
            console.print(f"CSM filter: [bold]{csm}[/bold]")
        console.print(f"Workers: [bold]{max_w}[/bold]  |  Local temp: [bold]{use_temp}[/bold]")
        if modules:
            console.print(f"Modules: [bold]{modules}[/bold]")
        console.print()

    # Scan for ready files
    files = scan_ready_files(settings, target_month=month, csm_filter=csm)
    if not files:
        console.print("[yellow]No ready files found for batch processing.[/yellow]")
        if not json_output:
            console.print(f"[dim]Searched: {settings.paths.watch_root}[/dim]")
        raise typer.Exit(0)

    if not json_output:
        # Show what we found
        scan_table = Table(title=f"Ready Files ({len(files)})", show_lines=False)
        scan_table.add_column("CSM", style="cyan")
        scan_table.add_column("Client ID")
        scan_table.add_column("File")
        scan_table.add_column("Size", justify="right")
        scan_table.add_column("Formatted", justify="center")
        for f in files:
            fmt = "[green]Yes[/green]" if f.is_formatted else "[yellow]No[/yellow]"
            scan_table.add_row(f.csm_name, f.client_id, f.filename, f"{f.file_size_mb:.1f} MB", fmt)
        console.print(scan_table)
        console.print()
    else:
        console.print(f"[green]Found {len(files)} client(s) to process (workers={max_w}).[/green]")

    # Parse module filter
    module_ids = _parse_modules(modules)

    # Run batch
    try:
        results = run_batch(
            files, settings, module_ids=module_ids,
            max_workers=max_w, use_local_temp=use_temp,
        )
    except Exception as exc:
        _display_error(exc)
        raise typer.Exit(1)

    # Output
    if json_output:
        data = [
            {
                "client_id": r.client_id,
                "client_name": r.client_name,
                "success": r.success,
                "elapsed": round(r.elapsed, 1),
                "slides": r.slide_count,
                "error": r.error,
            }
            for r in results
        ]
        ok = sum(1 for r in results if r.success)
        console.print_json(json.dumps({"results": data, "success": ok, "total": len(results)}))
    else:
        table = Table(title=f"Batch Results ({len(results)} clients)")
        table.add_column("Client ID", style="cyan")
        table.add_column("Name")
        table.add_column("Status", justify="center")
        table.add_column("Slides", justify="right")
        table.add_column("Time", justify="right")
        table.add_column("Error")

        for r in results:
            status = "[green]OK[/green]" if r.success else "[red]FAILED[/red]"
            table.add_row(
                r.client_id, r.client_name, status,
                str(r.slide_count), f"{r.elapsed:.1f}s",
                r.error[:50] if r.error else "",
            )
        console.print(table)

        ok = sum(1 for r in results if r.success)
        total_time = sum(r.elapsed for r in results)
        console.print(
            f"\n[{'green' if ok == len(results) else 'yellow'}]"
            f"Batch complete: {ok}/{len(results)} succeeded in {total_time:.1f}s"
            f"[/{'green' if ok == len(results) else 'yellow'}]"
        )

    if not all(r.success for r in results):
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

@app.command()
def check() -> None:
    """Validate config and verify all paths are accessible."""
    _setup()

    try:
        settings = _load_settings()
    except Exception as exc:
        _display_error(exc)
        raise typer.Exit(1)

    _show_config(settings, "Health Check")

    # Check registered analytics modules
    from ars_analysis.analytics.registry import REGISTRY
    try:
        from ars_analysis.analytics.registry import load_all_modules
        load_all_modules()
    except Exception:
        pass
    console.print(f"Analytics modules registered: [bold]{len(REGISTRY)}[/bold]")
    for mod_id, mod_cls in sorted(REGISTRY.items()):
        console.print(f"  {mod_id}: {mod_cls.__name__}")

    # Summary
    console.print()
    paths = settings.paths
    issues = []
    for label, path in [
        ("ars_base", paths.ars_base),
        ("retrieve_dir", paths.retrieve_dir),
        ("watch_root", paths.watch_root),
        ("presentations_dir", paths.presentations_dir),
    ]:
        try:
            if not path.exists():
                issues.append(f"{label}: {path}")
        except OSError:
            issues.append(f"{label}: {path} (network error)")

    if issues:
        console.print(Panel(
            "\n".join(f"[red]MISSING[/red] {p}" for p in issues)
            + "\n\n[dim]Run setup_folders.bat to create directories, or fix ars_config.json[/dim]",
            title="Issues Found",
            border_style="red",
        ))
        raise typer.Exit(1)
    else:
        console.print("[green]All paths accessible. Config looks good.[/green]")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@app.command()
def validate(
    file: str = typer.Argument(..., help="Path to ODD file to validate"),
) -> None:
    """Check an ODD file for required columns without running analysis."""
    _setup()

    file_path = Path(file)
    if not file_path.exists():
        _display_error(FileNotFoundError(f"File not found: {file_path}"))
        raise typer.Exit(1)

    from ars_analysis.pipeline.steps.load import _normalize_columns, _read_file

    try:
        df = _read_file(file_path)
        _normalize_columns(df, file_path)
    except DataError as exc:
        _display_error(exc)
        raise typer.Exit(1)

    console.print(f"[green]Valid: {len(df):,} rows, {len(df.columns)} columns[/green]")
    console.print(f"Columns: {', '.join(df.columns.tolist())}")


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

@app.command()
def init(
    directory: str | None = typer.Option(None, "--dir", help="Target directory"),
) -> None:
    """Set up a new machine: create config files, verify paths."""
    _setup()
    target = Path(directory) if directory else Path(".")
    configs_dir = target / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)

    # Copy default config if not present
    default_config = configs_dir / "ars_config.default.json"
    if not default_config.exists():
        console.print(f"[yellow]Place ars_config.default.json in {configs_dir}[/yellow]")
    else:
        console.print(f"[green]Config found: {default_config}[/green]")

    console.print("[green]Init complete[/green]")


# ---------------------------------------------------------------------------
# migrate
# ---------------------------------------------------------------------------

@app.command()
def migrate(
    old_config: str = typer.Argument(..., help="Path to old clients_config.json"),
    target: str | None = typer.Option(None, "--target", help="Target config path (default: configs/clients_config.json)"),
) -> None:
    """Merge an old clients_config.json into the new config location.

    Preserves existing entries. Adds missing clients. Enriches
    ICRate, NSF_OD_Fee, and BranchMapping from the old file.
    """
    _setup()

    from ars_analysis.config import migrate_config

    old_path = Path(old_config)
    if not old_path.exists():
        _display_error(FileNotFoundError(f"Old config not found: {old_path}"))
        raise typer.Exit(1)

    try:
        result = migrate_config(old_path, target_path=target)
    except Exception as exc:
        _display_error(exc)
        raise typer.Exit(1)

    console.print(f"[green]Migration complete -> {result['path']}[/green]")
    console.print(f"  {result['added']} client(s) added")
    console.print(f"  {result['enriched']} field(s) enriched (ICRate/NSF_OD_Fee/BranchMapping)")
    console.print(f"  {result['total']} total clients")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_client_info(config_path: str | None, file_path: Path) -> ClientInfo:
    """Load client info from config JSON or infer from filename."""
    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise ConfigError(f"Client config not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return ClientInfo(
            client_id=str(data.get("client_id", "0000")),
            client_name=data.get("client_name", "Unknown"),
            month=data.get("month", "2026.01"),
            eligible_stat_codes=data.get("eligible_stat_codes", []),
            eligible_prod_codes=data.get("eligible_prod_codes", []),
            nsf_od_fee=data.get("nsf_od_fee", 0.0),
            ic_rate=data.get("ic_rate", 0.0),
            dc_indicator=data.get("dc_indicator", "DC Indicator"),
            assigned_csm=data.get("assigned_csm", ""),
        )

    # Infer from filename: e.g., "1200_Test CU_2026.02.xlsx"
    stem = file_path.stem
    parts = stem.split("_", maxsplit=2)
    client_id = parts[0] if parts else "0000"
    client_name = parts[1] if len(parts) > 1 else "Unknown"
    month = parts[2] if len(parts) > 2 else "2026.01"

    return ClientInfo(client_id=client_id, client_name=client_name, month=month)
