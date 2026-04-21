import asyncio
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from stuntrpa import __version__
from stuntrpa.storage.scenario import Scenario

app = typer.Typer(
    name="stuntrpa",
    help="StuntRPA - Digital Twin ecosystem for RPA. Record & Replay web sessions.",
    no_args_is_help=True,
)
console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def version() -> None:
    console.print(f"stuntrpa {__version__}")


@app.command()
def record(
    url: str = typer.Argument(..., help="Initial URL to navigate to"),
    name: str = typer.Argument(..., help="Scenario name"),
    storage: Optional[Path] = typer.Option(None, "--storage", "-s", help="Custom storage directory"),
    headless: bool = typer.Option(False, "--headless", help="Run browser in headless mode"),
    browser: str = typer.Option("chromium", "--browser", "-b", help="Browser engine: chromium, firefox, webkit"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    _setup_logging(verbose)

    console.print(Panel(
        f"[bold]Recording:[/] {name}\n[url={url}]{url}[/]",
        title="StuntRPA Record",
        border_style="red",
    ))

    from stuntrpa.recorder.capture import record_session

    try:
        scenario = asyncio.run(record_session(
            url=url,
            name=name,
            storage_path=storage,
            headless=headless,
            browser_type=browser,
        ))
        stats = scenario.stats
        console.print(Panel(
            f"[green]Scenario saved successfully![/]\n\n"
            f"[bold]Name:[/] {name}\n"
            f"[bold]Requests:[/] {stats.get('total_requests', 0)}\n"
            f"[bold]Snapshots:[/] {stats.get('total_snapshots', 0)}\n"
            f"[bold]Duration:[/] {stats.get('duration_seconds', 0)}s\n"
            f"[bold]Location:[/] {scenario.path}",
            title="Recording Complete",
            border_style="green",
        ))
    except FileExistsError as e:
        console.print(f"[red]Error:[] {e}")
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Recording interrupted by user.[/]")
    except Exception as e:
        console.print(f"[red]Error:[] {e}")
        raise typer.Exit(code=1)


@app.command()
def replay(
    name: str = typer.Argument(..., help="Scenario name to replay"),
    storage: Optional[Path] = typer.Option(None, "--storage", "-s", help="Custom storage directory"),
    headless: bool = typer.Option(False, "--headless", help="Run browser in headless mode"),
    browser: str = typer.Option("chromium", "--browser", "-b", help="Browser engine: chromium, firefox, webkit"),
    simulate_latency: bool = typer.Option(False, "--simulate-latency", "-l", help="Simulate original network latency"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    _setup_logging(verbose)

    try:
        scenario = Scenario.load(name, storage)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[] {e}")
        raise typer.Exit(code=1)

    console.print(Panel(
        f"[bold]Replaying:[/] {name}\n"
        f"[bold]URL:[/] {scenario.start_url}\n"
        f"[bold]Latency simulation:[/] {'on' if simulate_latency else 'off'}",
        title="StuntRPA Replay",
        border_style="cyan",
    ))

    from stuntrpa.replayer.engine import replay_session

    try:
        asyncio.run(replay_session(
            scenario_name=name,
            storage_path=storage,
            simulate_latency=simulate_latency,
            headless=headless,
            browser_type=browser,
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Replay interrupted by user.[/]")
    except Exception as e:
        console.print(f"[red]Error:[] {e}")
        raise typer.Exit(code=1)


@app.command(name="list")
def list_scenarios(
    storage: Optional[Path] = typer.Option(None, "--storage", "-s", help="Custom storage directory"),
) -> None:
    scenarios = Scenario.list_all(storage)

    if not scenarios:
        console.print("[dim]No scenarios found.[/]")
        return

    table = Table(title="StuntRPA Scenarios", show_lines=True)
    table.add_column("Name", style="bold")
    table.add_column("Created")
    table.add_column("URL", max_width=50)
    table.add_column("Requests", justify="right")
    table.add_column("Snapshots", justify="right")
    table.add_column("Duration", justify="right")

    for name in scenarios:
        try:
            s = Scenario.load(name, storage)
            stats = s.stats
            table.add_row(
                name,
                s.created_at[:19] if s.created_at else "-",
                s.start_url,
                str(stats.get("total_requests", 0)),
                str(stats.get("total_snapshots", 0)),
                f"{stats.get('duration_seconds', 0)}s",
            )
        except Exception:
            table.add_row(name, "[red]error[/]", "", "", "", "")

    console.print(table)


@app.command()
def delete(
    name: str = typer.Argument(..., help="Scenario name to delete"),
    storage: Optional[Path] = typer.Option(None, "--storage", "-s", help="Custom storage directory"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    try:
        scenario = Scenario.load(name, storage)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[] {e}")
        raise typer.Exit(code=1)

    if not confirm:
        proceed = typer.confirm(f"Delete scenario '{name}' at {scenario.path}?")
        if not proceed:
            console.print("[dim]Cancelled.[/]")
            return

    Scenario.delete(name, storage)
    console.print(f"[green]Deleted scenario:[/] {name}")


@app.command()
def info(
    name: str = typer.Argument(..., help="Scenario name"),
    storage: Optional[Path] = typer.Option(None, "--storage", "-s", help="Custom storage directory"),
) -> None:
    try:
        scenario = Scenario.load(name, storage)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[] {e}")
        raise typer.Exit(code=1)

    stats = scenario.stats
    events = scenario.events

    console.print(Panel(
        f"[bold]Name:[/] {scenario.name}\n"
        f"[bold]URL:[/] {scenario.start_url}\n"
        f"[bold]Created:[/] {scenario.created_at}\n"
        f"[bold]Browser:[/] {scenario._metadata.get('browser_version', 'N/A')}\n"
        f"[bold]Playwright:[/] {scenario._metadata.get('playwright_version', 'N/A')}\n"
        f"[bold]Path:[/] {scenario.path}\n\n"
        f"[bold]Stats:[/]\n"
        f"  Requests: {stats.get('total_requests', 0)}\n"
        f"  Snapshots: {stats.get('total_snapshots', 0)}\n"
        f"  Duration: {stats.get('duration_seconds', 0)}s\n\n"
        f"[bold]Events ({len(events)}):[/]",
        title="Scenario Info",
        border_style="blue",
    ))

    if events:
        table = Table(show_lines=False, max_rows=20)
        table.add_column("#", style="dim", width=4)
        table.add_column("Time")
        table.add_column("Type")
        table.add_column("Details")

        for i, event in enumerate(events, 1):
            detail = ""
            if event.get("url"):
                detail = event["url"][:60]
            elif event.get("file"):
                detail = event["file"]
            table.add_row(
                str(i),
                event.get("timestamp", "")[:19],
                event.get("type", ""),
                detail,
            )
        console.print(table)
