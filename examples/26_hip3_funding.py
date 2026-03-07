"""
Moon Dev's HIP3 Funding Rate Dashboard
=======================================
Funding rate analysis for HIP3 tokenized assets (stocks, commodities, ETFs)
across xyz and cash dexes on Hyperliquid.

Built with love by Moon Dev
https://moondev.com

This dashboard shows:
- Top positive funding rates (longs paying shorts)
- Top negative funding rates (shorts paying longs)
- Current rates for tracked symbols (GOLD, TSLA, NVDA, etc.)
- All HIP3 symbols with annualized rates, mark prices, and OI

Usage: python 26_hip3_funding.py
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for API import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api import MoonDevAPI

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich import box

# Initialize Rich console - Moon Dev
console = Console()


def create_banner():
    """Create the Moon Dev HIP3 Funding Rate banner"""
    banner = """██╗  ██╗██╗██████╗ ██████╗     ███████╗██╗   ██╗███╗   ██╗██████╗ ██╗███╗   ██╗ ██████╗
██║  ██║██║██╔══██╗╚════██╗    ██╔════╝██║   ██║████╗  ██║██╔══██╗██║████╗  ██║██╔════╝
███████║██║██████╔╝ █████╔╝    █████╗  ██║   ██║██╔██╗ ██║██║  ██║██║██╔██╗ ██║██║  ███╗
██╔══██║██║██╔═══╝  ╚═══██╗    ██╔══╝  ██║   ██║██║╚██╗██║██║  ██║██║██║╚██╗██║██║   ██║
██║  ██║██║██║     ██████╔╝    ██║     ╚██████╔╝██║ ╚████║██████╔╝██║██║ ╚████║╚██████╔╝
╚═╝  ╚═╝╚═╝╚═╝     ╚═════╝     ╚═╝      ╚═════╝ ╚═╝  ╚═══╝╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝"""
    return Panel(
        Align.center(Text(banner, style="bold cyan")),
        title="[bold magenta]HIP3 FUNDING RATES[/bold magenta]",
        subtitle="[dim]Stocks | Commodities | ETFs | Indices | by Moon Dev[/dim]",
        border_style="bright_cyan",
        box=box.DOUBLE_EDGE,
        padding=(0, 1)
    )


def format_rate(rate_pct):
    """Format funding rate with color"""
    if rate_pct is None:
        return "[dim]N/A[/dim]"
    if rate_pct > 0.01:
        return f"[green]+{rate_pct:.4f}%[/green]"
    elif rate_pct < -0.01:
        return f"[red]{rate_pct:.4f}%[/red]"
    elif rate_pct > 0:
        return f"[dim green]+{rate_pct:.4f}%[/dim green]"
    elif rate_pct < 0:
        return f"[dim red]{rate_pct:.4f}%[/dim red]"
    return "[dim]0.0000%[/dim]"


def format_annualized(ann):
    """Format annualized rate with color"""
    if ann is None:
        return "[dim]N/A[/dim]"
    if ann > 10:
        return f"[bold green]+{ann:.1f}%[/bold green]"
    elif ann > 0:
        return f"[green]+{ann:.1f}%[/green]"
    elif ann < -10:
        return f"[bold red]{ann:.1f}%[/bold red]"
    elif ann < 0:
        return f"[red]{ann:.1f}%[/red]"
    return "[dim]0.0%[/dim]"


def format_usd(value):
    """Format USD value with commas"""
    if value is None or value == 0:
        return "[dim]--[/dim]"
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        return f"${value/1_000:.0f}K"
    return f"${value:,.2f}"


# ==================== TOP POSITIVE FUNDING ====================
def display_top_positive(data):
    """Display top positive funding rates - Moon Dev"""
    console.print(Panel(
        "[bold green]TOP POSITIVE FUNDING[/bold green]  [dim](longs paying shorts)[/dim]",
        border_style="green",
        padding=(0, 1)
    ))

    items = data.get('top_positive_funding', [])
    if not items:
        console.print("[dim]No positive funding data[/dim]")
        return

    table = Table(box=box.ROUNDED, border_style="green", header_style="bold cyan", padding=(0, 1))
    table.add_column("#", style="dim", width=3)
    table.add_column("Symbol", style="cyan", width=16)
    table.add_column("Rate (8h)", justify="right", width=12)
    table.add_column("Annualized", justify="right", width=12)

    for i, item in enumerate(items, 1):
        table.add_row(
            str(i),
            item['coin'],
            format_rate(item['rate_pct']),
            format_annualized(item['annualized'])
        )

    console.print(table)


# ==================== TOP NEGATIVE FUNDING ====================
def display_top_negative(data):
    """Display top negative funding rates - Moon Dev"""
    console.print(Panel(
        "[bold red]TOP NEGATIVE FUNDING[/bold red]  [dim](shorts paying longs)[/dim]",
        border_style="red",
        padding=(0, 1)
    ))

    items = data.get('top_negative_funding', [])
    if not items:
        console.print("[dim]No negative funding data[/dim]")
        return

    table = Table(box=box.ROUNDED, border_style="red", header_style="bold cyan", padding=(0, 1))
    table.add_column("#", style="dim", width=3)
    table.add_column("Symbol", style="cyan", width=16)
    table.add_column("Rate (8h)", justify="right", width=12)
    table.add_column("Annualized", justify="right", width=12)

    for i, item in enumerate(items, 1):
        table.add_row(
            str(i),
            item['coin'],
            format_rate(item['rate_pct']),
            format_annualized(item['annualized'])
        )

    console.print(table)


# ==================== CURRENT TRACKED RATES ====================
def display_current_rates(data):
    """Display rates for tracked HIP3 symbols - Moon Dev"""
    console.print(Panel(
        "[bold yellow]TRACKED SYMBOL RATES[/bold yellow]  [dim](GOLD, TSLA, NVDA, AAPL, USA500, etc.)[/dim]",
        border_style="yellow",
        padding=(0, 1)
    ))

    rates = data.get('current_rates', {})
    if not rates:
        console.print("[dim]No tracked rates available[/dim]")
        return

    table = Table(box=box.ROUNDED, border_style="yellow", header_style="bold cyan", padding=(0, 1))
    table.add_column("Symbol", style="cyan", width=16)
    table.add_column("Rate (8h)", justify="right", width=12)
    table.add_column("Annualized", justify="right", width=12)

    for coin, info in sorted(rates.items()):
        table.add_row(
            coin,
            format_rate(info.get('rate_pct')),
            format_annualized(info.get('annualized'))
        )

    console.print(table)


# ==================== ALL RATES ====================
def display_all_rates(data):
    """Display all HIP3 funding rates with mark price and OI - Moon Dev"""
    all_rates = data.get('all_rates', {})
    if not all_rates:
        console.print("[dim]No rate data available[/dim]")
        return

    console.print(Panel(
        f"[bold magenta]ALL HIP3 RATES[/bold magenta]  [dim]({len(all_rates)} symbols)[/dim]",
        border_style="magenta",
        padding=(0, 1)
    ))

    table = Table(box=box.ROUNDED, border_style="magenta", header_style="bold cyan", padding=(0, 1))
    table.add_column("Symbol", style="cyan", width=16)
    table.add_column("Rate (8h)", justify="right", width=12)
    table.add_column("Annualized", justify="right", width=12)
    table.add_column("Mark Price", justify="right", width=12)
    table.add_column("OI Value", justify="right", width=12)

    # Sort by annualized rate descending
    sorted_rates = sorted(all_rates.items(), key=lambda x: x[1].get('annualized', 0), reverse=True)

    for coin, info in sorted_rates:
        table.add_row(
            coin,
            format_rate(info.get('rate_pct')),
            format_annualized(info.get('annualized')),
            f"${info.get('mark_price', 0):,.2f}" if info.get('mark_price') else "[dim]--[/dim]",
            format_usd(info.get('oi_value'))
        )

    console.print(table)


# ==================== 24H HISTORY ====================
def display_history(data):
    """Display recent funding rate history - Moon Dev"""
    history = data.get('history_24h', [])
    if not history:
        console.print("[dim]No history data available[/dim]")
        return

    console.print(Panel(
        f"[bold blue]24H FUNDING HISTORY[/bold blue]  [dim]({len(history)} snapshots)[/dim]",
        border_style="blue",
        padding=(0, 1)
    ))

    table = Table(box=box.ROUNDED, border_style="blue", header_style="bold cyan", padding=(0, 1))
    table.add_column("Time", style="dim", width=20)
    table.add_column("Symbol", style="cyan", width=16)
    table.add_column("Rate", justify="right", width=14)
    table.add_column("Annualized", justify="right", width=12)
    table.add_column("Price", justify="right", width=12)

    for entry in history[:20]:  # Show last 20 entries
        time_str = entry.get('time', '')
        if len(time_str) > 19:
            time_str = time_str[:19].replace('T', ' ')

        table.add_row(
            time_str,
            entry.get('coin', ''),
            format_rate(entry.get('rate', 0) * 100 if entry.get('rate', 0) and abs(entry.get('rate', 0)) < 1 else entry.get('rate', 0)),
            format_annualized(entry.get('annualized')),
            f"${entry.get('price', 0):,.2f}" if entry.get('price') else "[dim]--[/dim]"
        )

    console.print(table)
    if len(history) > 20:
        console.print(f"[dim]  ... and {len(history) - 20} more entries[/dim]")


def create_footer():
    """Create footer with timestamp and branding - Moon Dev"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return Text(
        f"--- Moon Dev's HIP3 Funding Rates | {now} | api.moondev.com | Data updates ~15s ---",
        style="dim cyan",
        justify="center"
    )


def main():
    """Main function - Moon Dev's HIP3 Funding Rate Dashboard"""
    console.clear()
    console.print(create_banner())

    # Initialize API - Moon Dev
    console.print("[dim]Moon Dev connecting to API...[/dim]")
    api = MoonDevAPI()

    if not api.api_key:
        console.print(Panel(
            "[bold red]ERROR:[/bold red] No API key found!\n"
            "Set MOONDEV_API_KEY in .env | Get key at: [cyan]moondev.com[/cyan]",
            title="[red]Auth Error[/red]",
            border_style="red",
            padding=(0, 1)
        ))
        return

    console.print("[dim green]API connected - Moon Dev[/dim green]\n")

    # Fetch HIP3 funding data
    print("Moon Dev fetching HIP3 funding rates...")
    data = api.get_hlp_funding_hip3()

    if not isinstance(data, dict):
        console.print("[red]Error: unexpected response format[/red]")
        return

    # Show timestamp
    ts = data.get('timestamp', '')
    console.print(f"[dim]Last update: {ts}[/dim]\n")

    # Display all sections
    display_top_positive(data)
    console.print()

    display_top_negative(data)
    console.print()

    display_current_rates(data)
    console.print()

    display_all_rates(data)
    console.print()

    display_history(data)
    console.print()

    # Summary stats
    all_rates = data.get('all_rates', {})
    if all_rates:
        positive = sum(1 for v in all_rates.values() if v.get('rate_pct', 0) > 0)
        negative = sum(1 for v in all_rates.values() if v.get('rate_pct', 0) < 0)
        neutral = len(all_rates) - positive - negative
        total_oi = sum(v.get('oi_value', 0) for v in all_rates.values())

        summary = (
            f"[green]Positive: {positive}[/green] | "
            f"[red]Negative: {negative}[/red] | "
            f"[dim]Neutral: {neutral}[/dim] | "
            f"[yellow]Total OI: {format_usd(total_oi)}[/yellow] | "
            f"[cyan]Moon Dev[/cyan]"
        )
        console.print(Panel(summary, title="[bold cyan]HIP3 Funding Summary[/bold cyan]", border_style="cyan", padding=(0, 1)))

    console.print()
    console.print(create_footer())


if __name__ == "__main__":
    main()
