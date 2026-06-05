"""
🌙 Moon Dev's BTC Tick Stream
Built with love by Moon Dev 🚀

Live BTC tick stream modeled after the BTC liquidation dashboard.
Polls Moon Dev's tick endpoint on a cadence, dedupes new ticks, keeps a
rolling in-memory tape, and appends fresh ticks to a JSONL sink file so
external processes like arbitrage bots can consume a continuously-growing feed.

Usage:
    python examples/35_btc_tick_stream.py
    python examples/35_btc_tick_stream.py --symbol ETH --refresh 2
    python examples/35_btc_tick_stream.py --symbol BTC --output examples/data/btc_ticks.jsonl

Author: Moon Dev
"""

import argparse
import json
import os
import sys
import time
from collections import deque
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api import MoonDevAPI

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


DEFAULT_REFRESH_SECONDS = 5
DEFAULT_FETCH_DURATION = "10m"
DEFAULT_FETCH_LIMIT = 500
MAX_BUFFER_TICKS = 5000
RECENT_TAPE_ROWS = 30
MICRO_WINDOW_SECONDS = 60
SHORT_WINDOW_SECONDS = 300
MEDIUM_WINDOW_SECONDS = 900
BULL_COLOR = "bright_green"
BEAR_COLOR = "bright_red"
WARN_COLOR = "bright_yellow"


def parse_args():
    parser = argparse.ArgumentParser(description="Live tick stream for Moon Dev symbols")
    parser.add_argument("--symbol", default="BTC", help="Tracked symbol, default BTC")
    parser.add_argument("--refresh", type=int, default=DEFAULT_REFRESH_SECONDS, help="Refresh interval in seconds")
    parser.add_argument(
        "--duration",
        default=DEFAULT_FETCH_DURATION,
        choices=["10m", "1h", "4h", "24h", "7d"],
        help="Tick window to pull from the API each cycle",
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_FETCH_LIMIT, help="Max ticks to request")
    parser.add_argument(
        "--output",
        default=None,
        help="Optional JSONL output file. Defaults to examples/data/{symbol}_tick_stream.jsonl",
    )
    return parser.parse_args()


def format_price(price):
    if price is None:
        return "N/A"
    if abs(price) >= 1000:
        return f"${price:,.2f}"
    if abs(price) >= 1:
        return f"${price:,.4f}"
    return f"${price:,.6f}"


def format_count(value):
    return f"{value:,}"


def format_pace(value):
    if value >= 1000:
        return f"{value/1000:.1f}K/min"
    return f"{value:.1f}/min"


def format_pct(value):
    if value > 0:
        return f"+{value:.3f}%"
    return f"{value:.3f}%"


def format_dt(timestamp_ms):
    if not timestamp_ms:
        return "N/A"
    try:
        return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%H:%M:%S")
    except Exception:
        return "N/A"


def create_sparkline(prices, width=42):
    if not prices or len(prices) < 2:
        return "▄" * width, "dim"

    min_price = min(prices)
    max_price = max(prices)
    if min_price == max_price:
        return "▄" * min(len(prices), width), "dim"

    chars = "▁▂▃▄▅▆▇█"
    step = max(1, len(prices) // width)
    sampled = prices[::step][:width]
    sparkline = ""
    for price in sampled:
        normalized = (price - min_price) / (max_price - min_price)
        index = int(normalized * (len(chars) - 1))
        sparkline += chars[index]

    color = BULL_COLOR if prices[-1] > prices[0] else BEAR_COLOR if prices[-1] < prices[0] else "dim"
    return sparkline, color


def normalize_tick(tick, symbol):
    timestamp_ms = tick.get("t", tick.get("timestamp", 0))
    if isinstance(timestamp_ms, str):
        timestamp_ms = int(float(timestamp_ms))

    price = tick.get("p", tick.get("price"))
    price = float(price) if price is not None else None

    dt = tick.get("dt")
    if not dt and timestamp_ms:
        dt = datetime.fromtimestamp(timestamp_ms / 1000).isoformat()

    return {
        "symbol": symbol.upper(),
        "timestamp_ms": int(timestamp_ms) if timestamp_ms else 0,
        "price": price,
        "datetime": dt,
        "raw": tick,
    }


def tick_key(tick):
    return (tick["timestamp_ms"], tick["price"])


class TickStreamState:
    def __init__(self, symbol, output_path):
        self.symbol = symbol.upper()
        self.output_path = output_path
        self.ticks = deque(maxlen=MAX_BUFFER_TICKS)
        self.seen = set()
        self.total_seen = 0
        self.total_written = 0
        self.cycle_count = 0
        self.last_cycle_new = 0
        self.last_error = None
        self.last_warning = None
        self.last_api_tick_count = 0
        self.last_api_total_ticks = 0
        self.last_api_latest_price = None
        self.last_fetch_at = None
        self.started_at = time.time()

    def ingest(self, raw_ticks):
        new_ticks = []
        for raw_tick in raw_ticks:
            tick = normalize_tick(raw_tick, self.symbol)
            key = tick_key(tick)
            if key in self.seen or not tick["timestamp_ms"] or tick["price"] is None:
                continue
            self.seen.add(key)
            self.ticks.append(tick)
            new_ticks.append(tick)

        self.total_seen += len(new_ticks)
        self.last_cycle_new = len(new_ticks)
        self._trim_seen()
        return new_ticks

    def _trim_seen(self):
        active_keys = {tick_key(tick) for tick in self.ticks}
        if len(self.seen) > len(active_keys) * 2:
            self.seen = active_keys

    def persist_ticks(self, ticks):
        if not ticks:
            return

        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        with open(self.output_path, "a", encoding="utf-8") as handle:
            for tick in ticks:
                handle.write(
                    json.dumps(
                        {
                            "symbol": tick["symbol"],
                            "timestamp_ms": tick["timestamp_ms"],
                            "datetime": tick["datetime"],
                            "price": tick["price"],
                        }
                    )
                    + "\n"
                )
        self.total_written += len(ticks)


def window_ticks(ticks, seconds):
    if not ticks:
        return []
    cutoff = int(time.time() * 1000) - (seconds * 1000)
    return [tick for tick in ticks if tick["timestamp_ms"] >= cutoff]


def compute_stats(ticks):
    if not ticks:
        return {
            "count": 0,
            "first_price": 0,
            "last_price": 0,
            "change_pct": 0,
            "high": 0,
            "low": 0,
            "pace_per_min": 0,
            "avg_step_bps": 0,
        }

    prices = [tick["price"] for tick in ticks if tick["price"] is not None]
    if not prices:
        return {
            "count": len(ticks),
            "first_price": 0,
            "last_price": 0,
            "change_pct": 0,
            "high": 0,
            "low": 0,
            "pace_per_min": 0,
            "avg_step_bps": 0,
        }

    first_price = prices[0]
    last_price = prices[-1]
    change_pct = ((last_price - first_price) / first_price * 100) if first_price else 0

    moves_bps = []
    for idx in range(1, len(prices)):
        prev_price = prices[idx - 1]
        curr_price = prices[idx]
        if prev_price:
            moves_bps.append(abs(curr_price - prev_price) / prev_price * 10000)

    first_ts = ticks[0]["timestamp_ms"]
    last_ts = ticks[-1]["timestamp_ms"]
    duration_minutes = max((last_ts - first_ts) / 60000, 1 / 60)
    pace_per_min = len(ticks) / duration_minutes

    return {
        "count": len(ticks),
        "first_price": first_price,
        "last_price": last_price,
        "change_pct": change_pct,
        "high": max(prices),
        "low": min(prices),
        "pace_per_min": pace_per_min,
        "avg_step_bps": sum(moves_bps) / len(moves_bps) if moves_bps else 0,
    }


def create_header(symbol, refresh_seconds, output_path):
    banner = f"""  {symbol} TICK STREAM
  live polling -> rolling buffer -> jsonl sink"""
    return Panel(
        Align.center(Text(banner, style="bold bright_yellow")),
        title=f"🌙 [bold bright_magenta]MOON DEV's {symbol} TICK STREAM[/bold bright_magenta] 🌙",
        subtitle=f"[bold bright_cyan]Live Polling | Refreshes Every {refresh_seconds}s | JSONL Sink: {output_path}[/bold bright_cyan]",
        border_style="bright_yellow",
        box=box.DOUBLE_EDGE,
        padding=(0, 1),
    )


def build_dashboard(state, refresh_seconds):
    output = [create_header(state.symbol, refresh_seconds, state.output_path)]
    tick_list = list(state.ticks)

    stats_1m = compute_stats(window_ticks(tick_list, MICRO_WINDOW_SECONDS))
    stats_5m = compute_stats(window_ticks(tick_list, SHORT_WINDOW_SECONDS))
    stats_15m = compute_stats(window_ticks(tick_list, MEDIUM_WINDOW_SECONDS))
    all_stats = compute_stats(tick_list)

    summary = Text()
    summary.append(f"  {state.symbol} FLOW  ", style="bold bright_yellow")
    summary.append("| ", style="dim")
    summary.append(f"Buffered: {format_count(all_stats['count'])}", style="bold white")
    summary.append(" | ", style="dim")
    summary.append(f"New Cycle: +{format_count(state.last_cycle_new)}", style=f"bold {BULL_COLOR}" if state.last_cycle_new else "dim")
    summary.append(" | ", style="dim")
    summary.append(f"Written: {format_count(state.total_written)}", style="bold bright_cyan")
    summary.append(" | ", style="dim")
    summary.append(f"1m Pace: {format_pace(stats_1m['pace_per_min'])}", style="bold bright_magenta")
    summary.append(" | ", style="dim")
    summary.append(f"5m Avg Step: {stats_5m['avg_step_bps']:.2f} bps", style=WARN_COLOR)
    output.append(Panel(summary, border_style="bright_yellow", box=box.HEAVY, padding=(0, 0)))

    status = Text()
    status.append("  API STATUS  ", style="bold bright_cyan")
    status.append("| ", style="dim")
    status.append(f"cycle ticks: {format_count(state.last_api_tick_count)}", style="bold white")
    status.append(" | ", style="dim")
    status.append(f"total window: {format_count(state.last_api_total_ticks)}", style="bold white")
    status.append(" | ", style="dim")
    status.append(
        f"api latest: {format_price(state.last_api_latest_price) if state.last_api_latest_price is not None else 'N/A'}",
        style="bold bright_white",
    )
    status.append(" | ", style="dim")
    status.append(
        f"fetched: {state.last_fetch_at.strftime('%H:%M:%S') if state.last_fetch_at else 'never'}",
        style="dim",
    )
    output.append(Panel(status, border_style="bright_cyan", box=box.ROUNDED, padding=(0, 0)))

    if state.last_warning or state.last_error:
        warning = Text()
        warning.append("  STREAM NOTICE  ", style=f"bold {WARN_COLOR}")
        if state.last_warning:
            warning.append(state.last_warning, style=WARN_COLOR)
        if state.last_error:
            if state.last_warning:
                warning.append(" | ", style="dim")
            warning.append(state.last_error, style=BEAR_COLOR)
        output.append(Panel(warning, border_style=WARN_COLOR, box=box.ROUNDED, padding=(0, 0)))

    overview = Table(
        title=f"[bold bright_cyan]⚡ {state.symbol} MICROSTRUCTURE OVERVIEW[/]",
        box=box.HEAVY_EDGE,
        border_style="bright_cyan",
        header_style="bold bright_white on dark_blue",
        show_lines=True,
        padding=(0, 1),
        expand=True,
    )
    overview.add_column("WINDOW", justify="center", width=10)
    overview.add_column("LAST", justify="right", width=14)
    overview.add_column("CHANGE", justify="right", width=12)
    overview.add_column("LOW", justify="right", width=14)
    overview.add_column("HIGH", justify="right", width=14)
    overview.add_column("TICKS", justify="right", width=10)
    overview.add_column("PACE", justify="right", width=12)
    overview.add_column("AVG STEP", justify="right", width=12)

    for label, stats in [("1 MIN", stats_1m), ("5 MIN", stats_5m), ("15 MIN", stats_15m)]:
        if stats["change_pct"] > 0:
            change_str = f"[{BULL_COLOR}]{format_pct(stats['change_pct'])}[/]"
        elif stats["change_pct"] < 0:
            change_str = f"[{BEAR_COLOR}]{format_pct(stats['change_pct'])}[/]"
        else:
            change_str = "[dim]0.000%[/]"

        overview.add_row(
            label,
            format_price(stats["last_price"]) if stats["last_price"] else "N/A",
            change_str,
            format_price(stats["low"]) if stats["low"] else "N/A",
            format_price(stats["high"]) if stats["high"] else "N/A",
            format_count(stats["count"]),
            format_pace(stats["pace_per_min"]),
            f"{stats['avg_step_bps']:.2f} bps",
        )

    output.append(overview)

    prices = [tick["price"] for tick in tick_list if tick["price"] is not None]
    sparkline, spark_color = create_sparkline(prices)
    path_text = Text()
    path_text.append(f"  {state.symbol} ROLLING PATH  ", style="bold bright_magenta")
    path_text.append(f"{format_price(all_stats['last_price']) if all_stats['last_price'] else 'N/A'}", style="bold bright_white")
    path_text.append("  |  ", style="dim")
    path_text.append(f"Range: {format_price(all_stats['low'])} → {format_price(all_stats['high'])}" if all_stats["count"] else "Range: N/A", style="dim")
    path_text.append("\n\n")
    path_text.append(sparkline, style=spark_color)
    output.append(Panel(path_text, border_style="bright_magenta", box=box.HEAVY_EDGE, padding=(0, 1)))

    tape = Table(
        title=f"[bold bright_red]🔥 {state.symbol} TICK TAPE[/]  [dim]Most recent {RECENT_TAPE_ROWS} ticks[/]",
        box=box.HEAVY_EDGE,
        border_style="bright_red",
        header_style="bold bright_white on dark_red",
        show_lines=True,
        padding=(0, 1),
        expand=True,
    )
    tape.add_column("#", width=4, style="dim")
    tape.add_column("TIME", width=10, style="dim")
    tape.add_column("PRICE", width=16, justify="right")
    tape.add_column("Δ PX", width=12, justify="right")
    tape.add_column("Δ BPS", width=12, justify="right")
    tape.add_column("FLOW", width=12, justify="center")
    tape.add_column("BOT NOTE", min_width=20)

    recent_ticks = tick_list[-RECENT_TAPE_ROWS:]
    for idx, tick in enumerate(recent_ticks, 1):
        prev_tick = recent_ticks[idx - 2] if idx > 1 else None
        delta_px = 0
        delta_bps = 0
        flow = "[dim]FLAT[/]"
        note = "[dim]first print[/]"

        if prev_tick:
            delta_px = tick["price"] - prev_tick["price"]
            if prev_tick["price"]:
                delta_bps = (delta_px / prev_tick["price"]) * 10000
            if delta_px > 0:
                flow = f"[{BULL_COLOR}]UPTICK[/]"
                note = "[green]buyers lifting offers[/]"
            elif delta_px < 0:
                flow = f"[{BEAR_COLOR}]DOWNTICK[/]"
                note = "[red]sellers pressing bids[/]"
            else:
                note = "[dim]same price[/]"

        delta_px_str = f"[{BULL_COLOR}]+{delta_px:.4f}[/]" if delta_px > 0 else f"[{BEAR_COLOR}]{delta_px:.4f}[/]" if delta_px < 0 else "[dim]0.0000[/]"
        delta_bps_str = f"[{BULL_COLOR}]+{delta_bps:.2f}[/]" if delta_bps > 0 else f"[{BEAR_COLOR}]{delta_bps:.2f}[/]" if delta_bps < 0 else "[dim]0.00[/]"

        tape.add_row(
            str(idx),
            format_dt(tick["timestamp_ms"]),
            format_price(tick["price"]),
            delta_px_str,
            delta_bps_str,
            flow,
            note,
        )

    output.append(tape)

    footer = Text()
    footer.append("  🌙 Moon Dev Tick Stream", style="bold bright_yellow")
    footer.append(" | ", style="dim")
    footer.append(f"Cycle #{state.cycle_count}", style="bold white")
    footer.append(" | ", style="dim")
    footer.append(f"Running {(time.time() - state.started_at)/60:.1f} min", style="dim")
    footer.append(" | ", style="dim")
    footer.append(f"Last error: {state.last_error or 'none'}", style="dim")
    footer.append(" | ", style="dim")
    footer.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), style="dim")
    footer.append(" | Ctrl+C to exit", style="dim")
    output.append(Panel(footer, border_style="bright_yellow", box=box.ROUNDED, padding=(0, 0)))

    return Group(*output)


def main():
    args = parse_args()
    symbol = args.symbol.upper()
    console = Console()

    output_path = args.output or os.path.join("examples", "data", f"{symbol.lower()}_tick_stream.jsonl")

    console.clear()
    console.print(create_header(symbol, args.refresh, output_path))
    console.print(f"\n[bold bright_yellow]  🌙 Moon Dev:[/] Initializing {symbol} tick stream...")

    api = MoonDevAPI()
    if not api.api_key:
        console.print("[bold red]  ❌ No API key found! Set MOONDEV_API_KEY in your .env file[/]")
        return

    state = TickStreamState(symbol=symbol, output_path=output_path)
    console.print(f"[bold {BULL_COLOR}]  ✅ Moon Dev API connected[/]")
    console.print(f"[bold bright_yellow]  📡 Polling: /api/ticks/{symbol}?duration={args.duration}&limit={args.limit}[/]")
    console.print(f"[bold bright_cyan]  🧠 Sink file: {output_path}[/]")
    console.print(f"[dim]  🔄 Continuous polling every {args.refresh}s. New ticks append to JSONL for downstream bots.[/]\n")

    with Live(console=console, refresh_per_second=1, screen=True, vertical_overflow="crop") as live:
        while True:
            state.cycle_count += 1
            try:
                response = api.get_ticks(symbol, duration=args.duration, limit=args.limit)
                state.last_fetch_at = datetime.now()
                if isinstance(response, dict):
                    raw_ticks = response.get("ticks") or response.get("data") or []
                    state.last_api_tick_count = int(response.get("tick_count", len(raw_ticks)) or 0)
                    state.last_api_total_ticks = int(response.get("total_ticks", state.last_api_tick_count) or 0)
                    state.last_api_latest_price = response.get("latest_price")
                else:
                    raw_ticks = response if isinstance(response, list) else []
                    state.last_api_tick_count = len(raw_ticks)
                    state.last_api_total_ticks = len(raw_ticks)
                    state.last_api_latest_price = raw_ticks[-1].get("p") if raw_ticks else None

                new_ticks = state.ingest(raw_ticks)
                state.persist_ticks(new_ticks)
                state.last_error = None
                state.last_warning = None
                if not raw_ticks:
                    state.last_warning = (
                        f"API returned 0 ticks for {symbol} {args.duration} on this cycle. "
                        "Buffer retained; waiting for the next poll."
                    )
                live.update(build_dashboard(state, args.refresh))
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                state.last_error = str(exc)
                state.last_warning = "Fetch failed. Keeping prior buffered ticks on screen."
                live.update(build_dashboard(state, args.refresh))

            time.sleep(args.refresh)


if __name__ == "__main__":
    print("🌙 Moon Dev's BTC Tick Stream - Starting up...")
    print("🌙 Moon Dev says: Pulling the tick tape and keeping it flowing for the bots.\n")
    main()
