"""
🌙 Moon Dev's Bitcoin Liquidation Monitor + CSV Logger
Built with love by Moon Dev 🚀

Live dashboard showing BTC liquidations (last 5 min) from ALL exchanges.
Fetches 10m window from API, chops to 5 min. Saves CSV each cycle. Refreshes every 5s.

Author: Moon Dev
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Add parent directory to path for importing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import MoonDevAPI
from dotenv import load_dotenv
import pandas as pd

from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.live import Live
from rich import box

load_dotenv()

# ==================== MOON DEV CONFIG ====================
REFRESH_SECONDS = 5
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

BULL_COLOR = "bright_green"
BEAR_COLOR = "bright_red"
WARN_COLOR = "bright_yellow"

EXCHANGE_STYLE = {
    'hyperliquid': {'color': 'cyan', 'emoji': '💎', 'name': 'Hyperliquid'},
    'binance': {'color': 'yellow', 'emoji': '🟡', 'name': 'Binance'},
    'bybit': {'color': 'orange1', 'emoji': '🟠', 'name': 'Bybit'},
    'okx': {'color': 'bright_white', 'emoji': '⚪', 'name': 'OKX'},
}


def is_btc(symbol):
    s = str(symbol).upper().strip()
    return s in ['BTC', 'BTCUSDT', 'BTCUSD', 'BTC-USD', 'BTC-USDT', 'BTC-SWAP',
                 'BTCUSD_PERP', 'BTCUSDT-PERP', 'BTC-USD-SWAP', 'XBTUSD', 'XBTUSDT']


def extract_liquidations(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ['liquidations', 'data', 'events']:
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


def get_liq_value(liq):
    return float(liq.get('value', liq.get('usd_value', liq.get('value_usd',
                 liq.get('usd_size', liq.get('quantity', 0))))))


def get_liq_timestamp(liq):
    """Get liquidation timestamp as datetime, or None"""
    ts = liq.get('timestamp', liq.get('time', liq.get('trade_time', '')))
    if isinstance(ts, (int, float)):
        if ts > 1e12:
            return datetime.fromtimestamp(ts / 1000)
        return datetime.fromtimestamp(ts)
    if isinstance(ts, str) and ts:
        if 'T' in ts:
            return datetime.fromisoformat(ts.replace('Z', '+00:00').split('+')[0][:19])
    return None


def is_within_5min(liq):
    """Check if liquidation happened within the last 5 minutes"""
    t = get_liq_timestamp(liq)
    if not t:
        return True  # keep it if we can't parse the time
    return (datetime.now() - t).total_seconds() <= 300


def get_liq_side(liq):
    return str(liq.get('side', liq.get('direction', '?'))).upper()


def is_long(side):
    return side in ['LONG', 'BUY', 'B']


def format_usd(value):
    if value is None or value == 0:
        return "$0"
    if abs(value) >= 1_000_000_000:
        return f"${value/1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"${value/1_000:.1f}K"
    return f"${value:,.0f}"


def format_price(price):
    if price is None or price == 0:
        return "N/A"
    return f"${price:,.2f}"


def get_exchange_style(exchange):
    return EXCHANGE_STYLE.get(exchange.lower(), {'color': 'white', 'emoji': '🔹', 'name': exchange})


def create_header():
    banner = """  ₿ ██████╗ ████████╗ ██████╗    ██╗     ██╗ ██████╗ ███████╗
    ██╔══██╗╚══██╔══╝██╔════╝    ██║     ██║██╔═══██╗██╔════╝
    ██████╔╝   ██║   ██║         ██║     ██║██║   ██║███████╗
    ██╔══██╗   ██║   ██║         ██║     ██║██║▄▄ ██║╚════██║
    ██████╔╝   ██║   ╚██████╗    ███████╗██║╚██████╔╝███████║
    ╚═════╝    ╚═╝    ╚═════╝    ╚══════╝╚═╝ ╚══▀▀═╝╚══════╝"""
    return Panel(
        Align.center(Text(banner, style="bold bright_yellow")),
        title="🌙 [bold bright_magenta]MOON DEV's BTC LIQUIDATION MONITOR[/bold bright_magenta] 🌙",
        subtitle="[bold bright_cyan]All Exchanges | CSV Logger | Refreshes Every 5s[/bold bright_cyan]",
        border_style="bright_yellow",
        box=box.DOUBLE_EDGE,
        padding=(0, 1)
    )


def fetch_btc_liqs(api):
    """Fetch BTC liquidations from all exchanges"""
    all_btc_liqs = []
    exchange_counts = {}
    exchange_volumes = {}

    fetchers = [
        ("hyperliquid", lambda: api.get_liquidations("10m")),
        ("binance", lambda: api.get_binance_liquidations("10m")),
        ("bybit", lambda: api.get_bybit_liquidations("10m")),
        ("okx", lambda: api.get_okx_liquidations("10m")),
    ]

    for name, fetcher in fetchers:
        try:
            data = fetcher()
        except Exception as e:
            print(f"🌙 Moon Dev: {name} API hiccup, skipping this cycle - {e}")
            data = []
        liq_list = extract_liquidations(data)
        btc_liqs = [l for l in liq_list if is_btc(l.get('symbol', l.get('coin', '')))]
        for l in btc_liqs:
            l['_exchange'] = name
        all_btc_liqs.extend(btc_liqs)
        exchange_counts[name] = len(btc_liqs)
        exchange_volumes[name] = sum(get_liq_value(l) for l in btc_liqs)

    # Dedupe from combined endpoint
    try:
        combined = extract_liquidations(api.get_all_liquidations("10m"))
    except Exception as e:
        print(f"🌙 Moon Dev: Combined endpoint hiccup, skipping - {e}")
        combined = []
    combined_btc = [l for l in combined if is_btc(l.get('symbol', l.get('coin', '')))]

    existing_keys = set()
    for liq in all_btc_liqs:
        key = (str(liq.get('timestamp', liq.get('time', ''))), str(get_liq_value(liq)))
        existing_keys.add(key)

    for liq in combined_btc:
        key = (str(liq.get('timestamp', liq.get('time', ''))), str(get_liq_value(liq)))
        if key not in existing_keys:
            ex = liq.get('exchange', liq.get('source', 'unknown')).lower()
            liq['_exchange'] = ex
            all_btc_liqs.append(liq)

    # Filter to last 5 minutes only (API smallest is 10m, so we chop it)
    all_btc_liqs = [l for l in all_btc_liqs if is_within_5min(l)]

    # Recalculate exchange counts/volumes after filtering
    exchange_counts = {}
    exchange_volumes = {}
    for liq in all_btc_liqs:
        ex = liq.get('_exchange', 'unknown')
        exchange_counts[ex] = exchange_counts.get(ex, 0) + 1
        exchange_volumes[ex] = exchange_volumes.get(ex, 0) + get_liq_value(liq)

    # Sort by value descending
    all_btc_liqs.sort(key=lambda x: get_liq_value(x), reverse=True)

    return all_btc_liqs, exchange_counts, exchange_volumes


def save_csv(all_btc_liqs):
    """Save liquidations to CSV, return path"""
    if not all_btc_liqs:
        return None
    df = pd.DataFrame(all_btc_liqs)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = os.path.join(OUTPUT_DIR, f"btc_liquidations_{ts}.csv")
    df.to_csv(csv_file, index=False)
    return csv_file


def build_dashboard(api, cycle_count, last_csv):
    """Build the live dashboard"""
    output = []
    output.append(create_header())

    all_btc_liqs, exchange_counts, exchange_volumes = fetch_btc_liqs(api)

    # Save CSV every cycle
    csv_path = save_csv(all_btc_liqs)
    if csv_path:
        last_csv[0] = csv_path

    total_count = len(all_btc_liqs)
    total_vol = sum(get_liq_value(l) for l in all_btc_liqs)
    sides = [get_liq_side(l) for l in all_btc_liqs]
    long_count = sum(1 for s in sides if is_long(s))
    short_count = total_count - long_count
    long_vol = sum(get_liq_value(l) for l, s in zip(all_btc_liqs, sides) if is_long(s))
    short_vol = total_vol - long_vol

    # ==================== SUMMARY BAR ====================
    summary = Text()
    summary.append("  ₿ BTC LIQUIDATIONS (LAST 5 MIN)  ", style="bold bright_yellow")
    summary.append("| ", style="dim")
    summary.append(f"Total: {total_count}", style="bold white")
    summary.append(f" ({format_usd(total_vol)})", style="bold bright_yellow")
    summary.append(" | ", style="dim")
    summary.append(f"📈 Longs: {long_count} ({format_usd(long_vol)})", style=BULL_COLOR)
    summary.append(" | ", style="dim")
    summary.append(f"📉 Shorts: {short_count} ({format_usd(short_vol)})", style=BEAR_COLOR)

    if total_count > 0:
        long_pct = long_count / total_count * 100
        summary.append(" | ", style="dim")
        if long_pct > 60:
            summary.append(f"LONGS REKT ({long_pct:.0f}%)", style=f"bold {BEAR_COLOR}")
        elif long_pct < 40:
            summary.append(f"SHORTS REKT ({100-long_pct:.0f}%)", style=f"bold {BULL_COLOR}")
        else:
            summary.append(f"BALANCED", style=WARN_COLOR)

    output.append(Panel(summary, border_style="bright_yellow", box=box.HEAVY, padding=(0, 0)))

    # ==================== LONG/SHORT RATIO BAR ====================
    if total_count > 0:
        long_pct = long_count / total_count
        bar_width = 50
        long_bars = int(long_pct * bar_width)
        short_bars = bar_width - long_bars

        ratio_text = Text()
        ratio_text.append("  📈 LONGS ", style=f"bold {BULL_COLOR}")
        ratio_text.append("█" * long_bars, style=BULL_COLOR)
        ratio_text.append("█" * short_bars, style=BEAR_COLOR)
        ratio_text.append(" SHORTS 📉", style=f"bold {BEAR_COLOR}")
        output.append(Panel(
            Align.center(ratio_text),
            title=f"[bold white]Long/Short: {long_pct*100:.1f}% / {(1-long_pct)*100:.1f}%[/]",
            border_style="bright_magenta", padding=(0, 0)
        ))

    # ==================== LIQUIDATION TAPE ====================
    if all_btc_liqs:
        tape = Table(
            title=f"[bold bright_red]🔥 BTC LIQUIDATION FEED - ALL EXCHANGES | {total_count} Events | {format_usd(total_vol)}[/]",
            box=box.HEAVY_EDGE,
            border_style="bright_red",
            header_style="bold bright_white on dark_red",
            show_lines=True,
            padding=(0, 1),
            expand=True,
        )
        tape.add_column("#", style="dim", width=3)
        tape.add_column("EXCHANGE", justify="center", width=14)
        tape.add_column("SIDE", justify="center", width=10)
        tape.add_column("VALUE", style="bold bright_yellow", justify="right", width=14)
        tape.add_column("PRICE", justify="right", width=14)
        tape.add_column("QTY", justify="right", width=12)
        tape.add_column("TIME", style="dim", width=12)
        tape.add_column("IMPACT", justify="center", width=14)

        for i, liq in enumerate(all_btc_liqs[:25], 1):
            exchange = liq.get('_exchange', liq.get('exchange', liq.get('source', 'unknown')))
            style = get_exchange_style(exchange)
            ex_display = f"{style['emoji']} [{style['color']}]{style['name'][:8]}[/{style['color']}]"

            side = get_liq_side(liq)
            side_display = f"[{BULL_COLOR}]📈 LONG[/]" if is_long(side) else f"[{BEAR_COLOR}]📉 SHORT[/]"

            value = get_liq_value(liq)
            price = float(liq.get('price', liq.get('px', 0)))
            qty = float(liq.get('quantity', liq.get('sz', liq.get('size', liq.get('qty', liq.get('amount', 0))))))

            timestamp = liq.get('timestamp', liq.get('time', liq.get('trade_time', '')))
            time_str = "N/A"
            if timestamp:
                if isinstance(timestamp, (int, float)):
                    time_str = datetime.fromtimestamp(timestamp / 1000 if timestamp > 1e10 else timestamp).strftime("%H:%M:%S")
                elif isinstance(timestamp, str) and 'T' in timestamp:
                    time_str = timestamp.split('T')[1].split('.')[0]

            if value >= 1_000_000:
                impact = "[bold bright_yellow on red] 🐋🐋🐋 MEGA [/]"
            elif value >= 500_000:
                impact = "[bold bright_yellow] 🐋🐋 WHALE [/]"
            elif value >= 100_000:
                impact = "[bold bright_yellow] 🐋 BIG [/]"
            elif value >= 50_000:
                impact = f"[{WARN_COLOR}] ⚡ NOTABLE [/]"
            else:
                impact = "[dim] · normal [/]"

            rank = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else str(i)
            qty_str = f"{qty:,.4f}" if qty < 10 else f"{qty:,.2f}" if qty < 1000 else f"{qty:,.0f}"

            tape.add_row(
                rank, ex_display, side_display,
                f"[bold]{format_usd(value)}[/]",
                format_price(price), qty_str,
                time_str, impact,
            )

        output.append(tape)
    else:
        output.append(Panel(
            "[dim]  No BTC liquidations in the last 5 minutes. Market is calm... 🌙[/]",
            border_style="dim", padding=(0, 1)
        ))

    # ==================== TOTALS BOX ====================
    totals = Text()
    totals.append("\n  ₿ BTC LIQUIDATION TOTALS (LAST 5 MIN)\n\n", style="bold bright_yellow")
    totals.append(f"  Total Liquidations:  ", style="bold white")
    totals.append(f"{total_count:,}\n", style="bold bright_cyan")
    totals.append(f"  Total Volume:        ", style="bold white")
    totals.append(f"{format_usd(total_vol)}\n\n", style="bold bright_yellow")
    totals.append(f"  📈 Long Liquidations:  ", style=BULL_COLOR)
    totals.append(f"{long_count:,}  ({format_usd(long_vol)})\n", style=BULL_COLOR)
    totals.append(f"  📉 Short Liquidations: ", style=BEAR_COLOR)
    totals.append(f"{short_count:,}  ({format_usd(short_vol)})\n\n", style=BEAR_COLOR)

    # Per-exchange
    totals.append(f"  By Exchange:\n", style="bold white")
    for ex_name in ['hyperliquid', 'binance', 'bybit', 'okx']:
        style = EXCHANGE_STYLE[ex_name]
        ex_count = exchange_counts.get(ex_name, 0)
        ex_vol = exchange_volumes.get(ex_name, 0)
        totals.append(f"    {style['emoji']} {style['name']:<12}", style=f"bold {style['color']}")
        totals.append(f" {ex_count:>4} liqs  {format_usd(ex_vol):>10}\n", style="white")

    if last_csv[0]:
        totals.append(f"\n  💾 CSV: ", style="dim")
        totals.append(f"{os.path.basename(last_csv[0])}\n", style="dim")

    output.append(Panel(totals, title="[bold bright_magenta]💰 TOTALS[/]",
                       border_style="bright_magenta", box=box.DOUBLE_EDGE, padding=(0, 1)))

    return Group(*output)


def main():
    """🌙 Moon Dev's BTC Liquidation Monitor"""
    console = Console()
    console.clear()
    console.print(create_header())
    console.print("\n[bold bright_yellow]  🌙 Moon Dev:[/] Initializing BTC Liquidation Monitor...")

    api = MoonDevAPI()
    if not api.api_key:
        console.print("[bold red]  ❌ No API key found! Set MOONDEV_API_KEY in your .env file[/]")
        return

    console.print(f"[bold {BULL_COLOR}]  ✅ Moon Dev API connected[/]")
    console.print(f"[bold bright_yellow]  ₿  Monitoring: BTC liquidations across ALL exchanges[/]")
    console.print(f"[bold bright_cyan]  🔄 Refresh rate: {REFRESH_SECONDS}s[/]")
    console.print(f"[dim]  💾 CSV snapshots saving to: {OUTPUT_DIR}[/]\n")

    cycle_count = 0
    last_csv = [None]

    with Live(console=console, refresh_per_second=1, vertical_overflow="visible") as live:
        while True:
            cycle_count += 1
            try:
                dashboard = build_dashboard(api, cycle_count, last_csv)
                live.update(dashboard)
            except Exception as e:
                console.print(f"[bold yellow]  🌙 Moon Dev: Dashboard cycle #{cycle_count} hiccup, retrying next cycle - {e}[/]")
            time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    print("🌙 Moon Dev's BTC Liquidation Monitor - Starting up...")
    print("🌙 Moon Dev says: Watching Bitcoin liquidations across every exchange. Let's go.\n")
    main()
