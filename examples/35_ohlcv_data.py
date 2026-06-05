"""
🌙 Moon Dev's Open, High, Low, Close, Volume Data
Built with love by Moon Dev 🚀

Example client for the new bars layer:
- /api/universe
- /api/bars
- /api/bars/{symbol}

Important:
- Bars are computed from stored ticks
- `v` is currently "0" because true traded volume is not in the raw tick DB yet
- `n` is the number of ticks in the bar

Usage:
    python examples/35_ohlcv_data.py
    python examples/35_ohlcv_data.py --symbol BTC --interval 1h --limit 12
    python examples/35_ohlcv_data.py --symbols BTC,ETH,SOL --interval 1h --limit 8
"""

import argparse
import os
import sys
from datetime import datetime

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api import MoonDevAPI

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console()


def parse_args():
    parser = argparse.ArgumentParser(description="Moon Dev OHLCV-style bars example")
    parser.add_argument("--symbol", default="BTC", help="Primary symbol for single-symbol bars call")
    parser.add_argument("--symbols", default="BTC,ETH,SOL", help="Comma-separated symbols for bulk bars call")
    parser.add_argument("--interval", default="1h", help="Bar interval, default 1h")
    parser.add_argument("--limit", type=int, default=12, help="Max bars to display")
    return parser.parse_args()


def format_price(value):
    try:
        value = float(value)
    except Exception:
        return "N/A"
    if abs(value) >= 1000:
        return f"${value:,.2f}"
    if abs(value) >= 1:
        return f"${value:,.4f}"
    return f"${value:,.6f}"


def format_time(ts_ms):
    try:
        return datetime.fromtimestamp(int(ts_ms) / 1000).strftime("%m/%d %H:%M")
    except Exception:
        return "N/A"


def extract_universe_symbols(data):
    if not isinstance(data, dict):
        return []
    for key in ["symbols", "universe", "tracked_symbols"]:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def extract_bars(payload, symbol=None):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []

    for key in ["bars", "data", "candles"]:
        value = payload.get(key)
        if isinstance(value, list):
            return value

    if symbol:
        sym = str(symbol).upper()
        for key in [sym, sym.lower()]:
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                for nested in ["bars", "data", "candles"]:
                    nested_value = value.get(nested)
                    if isinstance(nested_value, list):
                        return nested_value

    by_symbol = payload.get("by_symbol") or payload.get("symbols")
    if isinstance(by_symbol, dict) and symbol:
        value = by_symbol.get(str(symbol).upper()) or by_symbol.get(str(symbol).lower())
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for nested in ["bars", "data", "candles"]:
                nested_value = value.get(nested)
                if isinstance(nested_value, list):
                    return nested_value

    return []


def extract_bulk_map(payload, requested_symbols):
    result = {}
    if isinstance(payload, dict):
        by_symbol = payload.get("by_symbol") or payload.get("symbols")
        if isinstance(by_symbol, dict):
            for symbol in requested_symbols:
                result[symbol] = extract_bars(by_symbol, symbol)
            return result

    for symbol in requested_symbols:
        result[symbol] = extract_bars(payload, symbol)
    return result


def show_universe(api):
    console.print("\n[bold cyan]🌌 UNIVERSE[/bold cyan]")
    data = api.get_universe()
    symbols = extract_universe_symbols(data)

    meta = Table(title="Tracked Universe", box=box.ROUNDED)
    meta.add_column("Field", style="cyan", width=24)
    meta.add_column("Value", style="white")
    meta.add_row("Symbol Count", str(data.get("count", len(symbols))))
    meta.add_row("Symbols Returned", str(len(symbols)))
    meta.add_row("Sample", ", ".join(symbols[:12]) if symbols else "N/A")
    meta.add_row("Generated", str(data.get("generated_at", data.get("timestamp", "N/A"))))
    console.print(meta)


def show_symbol_bars(api, symbol, interval, limit):
    console.print(f"\n[bold cyan]📊 SINGLE-SYMBOL BARS: {symbol} ({interval})[/bold cyan]")
    payload = api.get_bars_symbol(symbol, interval=interval, limit=limit)
    bars = extract_bars(payload, symbol)

    console.print(f"[green]✅ Loaded {len(bars)} bars for {symbol}[/green]")
    if not bars:
        console.print("[yellow]No bars returned for this symbol/interval.[/yellow]")
        return

    table = Table(title=f"{symbol} {interval} Bars", box=box.ROUNDED)
    table.add_column("Open Time", width=14)
    table.add_column("Open", justify="right", width=12)
    table.add_column("High", justify="right", width=12)
    table.add_column("Low", justify="right", width=12)
    table.add_column("Close", justify="right", width=12)
    table.add_column("Volume", justify="right", width=10)
    table.add_column("Ticks", justify="right", width=8)

    for bar in bars[-limit:]:
        table.add_row(
            format_time(bar.get("t")),
            format_price(bar.get("o")),
            format_price(bar.get("h")),
            format_price(bar.get("l")),
            format_price(bar.get("c")),
            str(bar.get("v", "0")),
            str(bar.get("n", 0)),
        )
    console.print(table)


def show_bulk_bars(api, symbols, interval, limit):
    console.print(f"\n[bold cyan]🧺 BULK BARS: {', '.join(symbols)} ({interval})[/bold cyan]")
    payload = api.get_bars(symbols=symbols, interval=interval, limit=limit)
    bulk = extract_bulk_map(payload, symbols)

    table = Table(title="Latest Bulk Bar Snapshot", box=box.ROUNDED)
    table.add_column("Symbol", style="cyan", width=8)
    table.add_column("Open Time", width=14)
    table.add_column("Open", justify="right", width=12)
    table.add_column("High", justify="right", width=12)
    table.add_column("Low", justify="right", width=12)
    table.add_column("Close", justify="right", width=12)
    table.add_column("Volume", justify="right", width=10)
    table.add_column("Ticks", justify="right", width=8)

    loaded = 0
    for symbol in symbols:
        bars = bulk.get(symbol, [])
        if not bars:
            table.add_row(symbol, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "0")
            continue
        loaded += 1
        bar = bars[-1]
        table.add_row(
            symbol,
            format_time(bar.get("t")),
            format_price(bar.get("o")),
            format_price(bar.get("h")),
            format_price(bar.get("l")),
            format_price(bar.get("c")),
            str(bar.get("v", "0")),
            str(bar.get("n", 0)),
        )

    console.print(f"[green]✅ Bulk response covered {loaded}/{len(symbols)} requested symbols[/green]")
    console.print(table)


def main():
    args = parse_args()
    api = MoonDevAPI()
    symbols = [symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()]

    if not api.api_key:
        console.print("[bold red]❌ No API key found! Set MOONDEV_API_KEY in your .env file[/bold red]")
        return

    console.print(
        Panel(
            "[bold white]Open, High, Low, Close, Volume Data[/bold white]\n"
            "[dim]Bars are server-computed from ticks. `v` is currently 0 and `n` is tick count.[/dim]",
            title="🌙 Moon Dev OHLCV Data",
            border_style="cyan",
            box=box.DOUBLE_EDGE,
        )
    )

    try:
        show_universe(api)
        show_symbol_bars(api, args.symbol.upper(), args.interval, args.limit)
        show_bulk_bars(api, symbols, args.interval, args.limit)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "N/A"
        if status == 404:
            console.print(
                Panel(
                    "[bold yellow]The new bars routes are not live on this host yet.[/bold yellow]\n"
                    "[dim]Production still returns 404 for /api/universe and /api/bars right now.[/dim]\n"
                    "[dim]Server-side note from your rollout says the remaining step is:[/dim]\n"
                    "[bold white]sudo systemctl restart user-positions-api.service[/bold white]",
                    title="Endpoint Not Live Yet",
                    border_style="yellow",
                )
            )
            return
        raise


if __name__ == "__main__":
    main()
