"""KRAKEN CLI — `kraken` entrypoint.

Commands:
  kraken voyage:run  VOYAGE_NAME  [--params JSON]
  kraken voyage:list
  kraken voyage:lint
  kraken voyage:compile VOYAGE_NAME [--params JSON]
  kraken api:serve    [--host HOST] [--port PORT]
  kraken status
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

import click
import structlog
from rich.console import Console
from rich.table import Table

from kraken.models import VoyageKind
from kraken.voyages.compiler import VoyageCompileError, compile_voyage, list_voyages, validate_voyage

console = Console()
logger = structlog.get_logger(__name__)


def _parse_params(params_json: str | None) -> dict[str, Any]:
    if not params_json:
        return {}
    try:
        result = json.loads(params_json)
        if not isinstance(result, dict):
            raise click.BadParameter("--params must be a JSON object")
        return result  # type: ignore[return-value]
    except json.JSONDecodeError as exc:
        raise click.BadParameter(f"Invalid JSON: {exc}") from exc


@click.group()
@click.version_option(package_name="kraken")
def cli() -> None:
    """KRAKEN — one SQL query, every system, every voyage."""


# ── voyage commands ───────────────────────────────────────────────────────────

@cli.command("voyage:run")
@click.argument("voyage_name")
@click.option("--params", default=None, help="JSON params for the voyage")
@click.option("--dry-run", is_flag=True, help="Compile and print SQL without executing")
@click.option("--voyage-id", default=None, help="Override voyage ID (for tracing)")
def voyage_run(voyage_name: str, params: str | None, dry_run: bool, voyage_id: str | None) -> None:
    """Run a named voyage against Coral."""
    import uuid

    parsed_params = _parse_params(params)
    vid = voyage_id or str(uuid.uuid4())

    try:
        compiled = compile_voyage(voyage_name, parsed_params)
    except VoyageCompileError as exc:
        console.print(f"[bold red]Compile error:[/bold red] {exc}")
        sys.exit(1)

    if dry_run:
        console.print(f"[bold cyan]Voyage:[/bold cyan] {compiled.name}")
        console.print(f"[bold cyan]Sources:[/bold cyan] {', '.join(compiled.required_sources)}")
        console.print(f"[bold cyan]Params:[/bold cyan] {json.dumps(compiled.params, indent=2)}")
        console.print("\n[bold cyan]SQL:[/bold cyan]")
        console.print(compiled.sql)
        return

    console.print(f"[bold green]Running voyage:[/bold green] {compiled.name} (voyage_id={vid})")

    from kraken.crew import run_sync
    try:
        result = run_sync(
            question=f"run voyage {voyage_name}",
            params=parsed_params,
            voyage_id=vid,
        )
    except Exception as exc:
        console.print(f"[bold red]Voyage failed:[/bold red] {exc}")
        sys.exit(1)

    rows = result.get("findings", [{}])
    if rows and isinstance(rows[0], dict):
        _render_table(rows)
    console.print(f"\n[bold green]✓[/bold green] Voyage complete — {len(rows)} finding(s)")


@cli.command("voyage:list")
def voyage_list() -> None:
    """List all registered voyages."""
    voyages = list_voyages()
    table = Table(title="Registered Voyages", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Target Agent", style="green")
    table.add_column("Sources", style="yellow")
    table.add_column("Description", style="white", max_width=60)
    for v in voyages:
        table.add_row(
            v["name"],
            v.get("target_agent") or "—",
            ", ".join(v.get("required_sources", [])),
            (v.get("description") or "")[:80],
        )
    console.print(table)


@cli.command("voyage:lint")
@click.argument("voyage_name", default="all")
def voyage_lint(voyage_name: str) -> None:
    """Validate voyage YAML(s). Checks SQL quality rules."""
    if voyage_name == "all":
        voyages = list_voyages()
        targets = [v["name"] for v in voyages]
    else:
        targets = [voyage_name]

    all_ok = True
    for name in targets:
        errors = validate_voyage(name)
        if errors:
            console.print(f"[bold red]✗[/bold red] {name}:")
            for err in errors:
                console.print(f"  • {err}")
            all_ok = False
        else:
            console.print(f"[bold green]✓[/bold green] {name}")

    if not all_ok:
        sys.exit(1)


@cli.command("voyage:compile")
@click.argument("voyage_name")
@click.option("--params", default=None, help="JSON params for the voyage")
def voyage_compile(voyage_name: str, params: str | None) -> None:
    """Compile a voyage and print the rendered SQL."""
    parsed_params = _parse_params(params)
    try:
        compiled = compile_voyage(voyage_name, parsed_params)
    except VoyageCompileError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)

    console.print(f"-- Voyage: {compiled.name}")
    console.print(f"-- Sources: {', '.join(compiled.required_sources)}")
    console.print(f"-- Params: {json.dumps(compiled.params)}")
    console.print()
    console.print(compiled.sql)


# ── api commands ──────────────────────────────────────────────────────────────

@cli.command("api:serve")
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8000, show_default=True)
@click.option("--reload", is_flag=True, help="Enable hot reload (dev only)")
def api_serve(host: str, port: int, reload: bool) -> None:
    """Start the KRAKEN FastAPI server."""
    import uvicorn
    uvicorn.run(
        "kraken.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# ── status command ────────────────────────────────────────────────────────────

@cli.command("status")
def status() -> None:
    """Show KRAKEN system status — Coral connection, blackboard, voyages."""
    from pathlib import Path

    voyages = list_voyages()
    bb_path = Path.home() / ".kraken"

    table = Table(title="KRAKEN Status", show_header=True)
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Detail")

    # Voyages
    table.add_row("Voyages", "✓", f"{len(voyages)} registered")

    # Blackboard
    findings_path = bb_path / "findings.parquet"
    plans_path = bb_path / "plans.parquet"
    bb_status = "✓" if findings_path.exists() and plans_path.exists() else "○ not initialized"
    table.add_row("Blackboard", bb_status, str(bb_path))

    # Reef Memory
    reef_path = bb_path / "reef"
    reef_status = "✓" if reef_path.exists() else "○ empty"
    table.add_row("Reef Memory", reef_status, str(reef_path))

    # Coral (check if binary exists)
    import shutil
    coral_bin = shutil.which("coral")
    coral_status = "✓" if coral_bin else "✗ not found — install Coral"
    table.add_row("Coral CLI", coral_status, coral_bin or "run: cargo install coral-cli")

    console.print(table)


# ── helpers ───────────────────────────────────────────────────────────────────

def _render_table(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    table = Table(show_header=True, header_style="bold blue")
    columns = list(rows[0].keys())
    for col in columns:
        table.add_column(col)
    for row in rows[:20]:
        table.add_row(*[str(row.get(c, "")) for c in columns])
    if len(rows) > 20:
        table.add_row(*["..." for _ in columns])
    console.print(table)


if __name__ == "__main__":
    cli()
