"""
🌙 Moon Dev's BTC Funding Rate & Open Interest Comparison
Built with love by Moon Dev 🚀

Compares BTC funding rates (annualized) and open interest between
Hyperliquid and Binance. Shows the real cost of holding a position
and where the money is sitting.

NOTE: Hyperliquid pays funding every HOUR (×24×365 to annualize).
      Binance pays funding every 8 HOURS (×3×365 to annualize).

Usage:
    python 33_btc_funding_oi_comparison.py

Author: Moon Dev
"""

import requests
import time
from datetime import datetime, timezone

from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich import box
from rich.align import Align

# ==================== MOON DEV CONFIGURATION ====================
REFRESH_SECONDS = 15

# Colors - Moon Dev palette
BULL_COLOR = "bright_green"
BEAR_COLOR = "bright_red"
NEUTRAL_COLOR = "bright_yellow"
HL_COLOR = "bright_cyan"
BN_COLOR = "bright_yellow"
ACCENT = "bright_magenta"


def fmt_usd(value):
    """Moon Dev - Format large dollar values"""
    if value is None:
        return "$0"
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    if value >= 1_000:
        return f"${value / 1_000:,.1f}K"
    return f"${value:,.0f}"


def get_hyperliquid_data():
    """
    🌙 Moon Dev - Fetch BTC funding rate + OI from Hyperliquid
    Hyperliquid funding is paid every 1 HOUR (not 8h like Binance)
    """
    url = "https://api.hyperliquid.xyz/info"
    payload = {"type": "metaAndAssetCtxs"}

    response = requests.post(url, json=payload, timeout=10)
    data = response.json()

    universe = data[0]["universe"]
    asset_ctxs = data[1]

    for i, asset in enumerate(universe):
        if asset["name"] == "BTC":
            ctx = asset_ctxs[i]
            hourly_rate = float(ctx["funding"]) * 100
            mark_price = float(ctx["markPx"])
            open_interest = float(ctx["openInterest"])
            oi_usd = open_interest * mark_price

            # Hyperliquid: hourly funding → annualized = rate × 24 × 365
            annualized = hourly_rate * 24 * 365

            return {
                "hourly_rate": hourly_rate,
                "annualized": annualized,
                "mark_price": mark_price,
                "oi_coins": open_interest,
                "oi_usd": oi_usd,
            }


def get_binance_data():
    """
    🌙 Moon Dev - Fetch BTC funding rate + OI from Binance
    Binance funding is paid every 8 HOURS (3× per day)
    """
    fr_url = "https://fapi.binance.com/fapi/v1/fundingRate"
    fr_response = requests.get(fr_url, params={"symbol": "BTCUSDT", "limit": 1}, timeout=10)
    fr_data = fr_response.json()
    eight_hour_rate = float(fr_data[0]["fundingRate"]) * 100
    annualized = eight_hour_rate * 3 * 365

    mark_data = requests.get("https://fapi.binance.com/fapi/v1/premiumIndex", params={"symbol": "BTCUSDT"}, timeout=10).json()
    mark_price = float(mark_data["markPrice"])
    next_funding_ms = int(mark_data["nextFundingTime"])
    next_funding_dt = datetime.fromtimestamp(next_funding_ms / 1000, tz=timezone.utc)

    oi_data = requests.get("https://fapi.binance.com/fapi/v1/openInterest", params={"symbol": "BTCUSDT"}, timeout=10).json()
    oi_coins = float(oi_data["openInterest"])
    oi_usd = oi_coins * mark_price

    return {
        "eight_hour_rate": eight_hour_rate,
        "annualized": annualized,
        "mark_price": mark_price,
        "oi_coins": oi_coins,
        "oi_usd": oi_usd,
        "next_funding_utc": next_funding_dt.strftime("%H:%M UTC"),
    }


def build_dashboard():
    """🌙 Moon Dev - Build the compact funding & OI dashboard"""
    output = []

    # Header
    header_text = Text()
    header_text.append("  ₿ BTC FUNDING & OI  ", style="bold bright_yellow")
    header_text.append("Hyperliquid vs Binance", style="bold bright_cyan")
    output.append(Panel(header_text, title="🌙 [bold bright_magenta]MOON DEV[/] 🌙", border_style="bright_yellow", box=box.DOUBLE_EDGE, padding=(0, 1)))

    hl = get_hyperliquid_data()
    bn = get_binance_data()

    # ==================== FUNDING RATES TABLE ====================
    fr_table = Table(
        title="[bold bright_magenta]💰 FUNDING RATES (ANNUALIZED) 💰[/]",
        box=box.HEAVY_EDGE,
        border_style=ACCENT,
        header_style="bold bright_white on dark_magenta",
        show_lines=True,
        padding=(0, 1),
        expand=True,
    )
    fr_table.add_column("", style="bold bright_white", justify="right", width=12)
    fr_table.add_column("🔵 HYPERLIQUID", justify="center", style=HL_COLOR)
    fr_table.add_column("🟡 BINANCE", justify="center", style=BN_COLOR)
    fr_table.add_column("SPREAD", justify="center")

    # Current rate row
    fr_table.add_row(
        "Rate",
        f"{hl['hourly_rate']:+.6f}%/hr",
        f"{bn['eight_hour_rate']:+.6f}%/8h",
        f"Next BN: {bn['next_funding_utc']}",
    )

    # Annualized row
    hl_ann = hl["annualized"]
    bn_ann = bn["annualized"]
    diff = hl_ann - bn_ann
    hl_c = BULL_COLOR if hl_ann >= 0 else BEAR_COLOR
    bn_c = BULL_COLOR if bn_ann >= 0 else BEAR_COLOR
    diff_c = BULL_COLOR if diff >= 0 else BEAR_COLOR
    fr_table.add_row(
        "[bold]ANNUAL[/]",
        f"[bold {hl_c}]{hl_ann:+.2f}%[/]",
        f"[bold {bn_c}]{bn_ann:+.2f}%[/]",
        f"[bold {diff_c}]{diff:+.2f}%[/]",
    )

    # Mark price row
    price_diff = hl["mark_price"] - bn["mark_price"]
    fr_table.add_row(
        "Mark",
        f"${hl['mark_price']:,.2f}",
        f"${bn['mark_price']:,.2f}",
        f"${price_diff:+,.2f}",
    )

    # ==================== OPEN INTEREST TABLE ====================
    oi_table = Table(
        title="[bold bright_red]📊 OPEN INTEREST 📊[/]",
        box=box.HEAVY_EDGE,
        border_style="bright_red",
        header_style="bold bright_white on dark_red",
        show_lines=True,
        padding=(0, 1),
        expand=True,
    )
    oi_table.add_column("", style="bold bright_white", justify="right", width=12)
    oi_table.add_column("🔵 HYPERLIQUID", justify="center", style=HL_COLOR)
    oi_table.add_column("🟡 BINANCE", justify="center", style=BN_COLOR)
    oi_table.add_column("COMBINED", justify="center")

    hl_oi = hl["oi_usd"]
    bn_oi = bn["oi_usd"]
    total_oi = hl_oi + bn_oi
    hl_pct = (hl_oi / total_oi * 100) if total_oi > 0 else 0
    bn_pct = (bn_oi / total_oi * 100) if total_oi > 0 else 0

    oi_table.add_row(
        "[bold]OI (USD)[/]",
        f"[bold {HL_COLOR}]{fmt_usd(hl_oi)}[/]",
        f"[bold {BN_COLOR}]{fmt_usd(bn_oi)}[/]",
        f"[bold white]{fmt_usd(total_oi)}[/]",
    )
    oi_table.add_row(
        "OI (BTC)",
        f"{hl['oi_coins']:,.1f}",
        f"{bn['oi_coins']:,.1f}",
        f"{hl['oi_coins'] + bn['oi_coins']:,.1f}",
    )
    oi_table.add_row(
        "Share",
        f"{hl_pct:.1f}%",
        f"{bn_pct:.1f}%",
        "",
    )

    output.append(oi_table)

    # ==================== FUNDING RATES TABLE (below OI) ====================
    output.append(fr_table)

    # Footer
    now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    output.append(Panel(
        f"  [dim]{now} | {REFRESH_SECONDS}s refresh | 🌙 Moon Dev[/]",
        border_style="dim", box=box.ROUNDED, padding=(0, 0),
    ))

    return Group(*output)


def main():
    """🌙 Moon Dev's BTC Funding & OI Tracker"""
    console = Console()
    console.clear()
    console.print("[bold bright_yellow]  🌙 Moon Dev:[/] BTC Funding & OI Tracker starting...")
    console.print("[dim]  📡 Hyperliquid (hourly) vs Binance (8h) funding...[/]\n")

    with Live(console=console, refresh_per_second=1, vertical_overflow="visible") as live:
        while True:
            dashboard = build_dashboard()
            live.update(dashboard)
            time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    print("🌙 Moon Dev's BTC Funding & OI Tracker - Starting up...")
    print("🌙 Moon Dev says: Know what you're paying to hold that position.\n")
    main()
