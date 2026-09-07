from pathlib import Path
from typing import Iterable

from rich.align import Align
from rich.console import Console
from rich.console import Group
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from .config import APP_NAME, INSTAGRAM
from .quality import QualityOption, quality_choices

console = Console()


def banner() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]FSD Downloader[/bold cyan]\n[white]Fast, simple video and playlist downloads[/white]",
            border_style="cyan",
        )
    )


def ask_url(default: str | None = None) -> str:
    if default:
        return default
    return Prompt.ask("[bold]Video or playlist URL[/bold]").strip()


def choose_quality() -> QualityOption:
    table = Table(title="Choose quality", show_header=True, header_style="bold cyan")
    table.add_column("#", justify="right")
    table.add_column("Option")
    options = quality_choices()
    for index, option in enumerate(options, start=1):
        table.add_row(str(index), option.label)
    console.print(table)
    choice = IntPrompt.ask("Quality", choices=[str(i) for i in range(1, len(options) + 1)], default=6)
    return options[choice - 1]


def show_playlist_info(title: str, total: int) -> None:
    console.print(
        Panel(
            f"[bold]Playlist:[/bold] {title}\n[bold]Episodes:[/bold] {total}",
            title="Detected playlist",
            border_style="green",
        )
    )


def show_video_info(title: str) -> None:
    console.print(Panel(f"[bold]Video:[/bold] {title}", title="Detected video", border_style="green"))


def show_success(completed: int, skipped: int, output_folder: Path, failed: int = 0) -> None:
    title = "Downloads failed" if failed and completed == 0 else "Completed with errors" if failed else "Done"
    border = "yellow" if failed else "green"
    body = (
        f"[bold green]Completed files:[/bold green] {completed}\n"
        f"[bold yellow]Skipped files:[/bold yellow] {skipped}\n"
        f"[bold red]Failed files:[/bold red] {failed}\n"
        f"[bold cyan]Output folder:[/bold cyan] {output_folder}"
    )
    console.line()
    console.print(Panel(body, title=title, border_style=border))
    console.print(instagram_footer())


def instagram_footer() -> Panel:
    heading = Text("Follow me on Instagram", style="bold white")
    handle = Text(INSTAGRAM, style="bold magenta")
    return Panel.fit(
        Group(Align.center(heading), Align.center(handle)),
        title="Instagram",
        border_style="magenta",
        padding=(1, 4),
    )


def show_error(message: str, hints: Iterable[str] = ()) -> None:
    details = "\n".join(f"- {hint}" for hint in hints)
    text = f"[bold red]{message}[/bold red]"
    if details:
        text += f"\n\n{details}"
    console.print(Panel(text, title="Download stopped", border_style="red"))
