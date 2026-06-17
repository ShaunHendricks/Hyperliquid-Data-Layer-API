"""
Moon Dev's Hyperliquid Direct-Proxy Dashboard
=============================================
Drop-in replacements for the Hyperliquid SDK that kill 429s on repeated polls.

    info.user_state(addr)   ->  GET /api/hl/clearinghouse/{addr}
    info.open_orders(addr)  ->  GET /api/hl/open_orders/{addr}

Both endpoints try Moon Dev's local HL node first and transparently fall back to
api.hyperliquid.xyz, so a 200 ALWAYS means real data - never a silent zero/[] on
upstream failure. That makes them safe to drive a live trading bot.

Built with love by Moon Dev

Usage: python 36_hl_direct_proxy.py [address] [coin]
       python 36_hl_direct_proxy.py 0xdfc24b077bc1425ad1dea75bcb6f8158e10df303
       python 36_hl_direct_proxy.py 0xc71cc6f1d8b6d1b0ee55cfc70cd210b2bd1bc506 BTC
"""

import sys
import os
from datetime import datetime

# Add parent directory to path to import api.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api import MoonDevAPI

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.align import Align


console = Console()


def create_banner():
    """Moon Dev branded header banner"""
    banner = """
 _   _ _       ____ ____   _____  ___ ____   __
| | | | |     |  _ \\  _ \\ / _ \\ \\/ / \\ \\ / /
| |_| | |     | |_) | |_) | | | \\  /  \\ V /
|  _  | |___  |  __/|  _ <| |_| /  \\   | |
|_| |_|_____| |_|   |_| \\_\\\\___/_/\\_\\  |_|
"""
    return Panel(
        Align.center(Text(banner, style="bold cyan")),
        title="[bold magenta]MOON DEV'S HYPERLIQUID DIRECT-PROXY[/bold magenta]",
        subtitle="[dim]info.user_state + info.open_orders, no rate limits[/dim]",
        border_style="bright_cyan",
        box=box.DOUBLE_EDGE,
        padding=(0, 1),
    )


def format_usd(value):
    """Format a USD value with commas and dollar sign"""
    if value is None:
        return "$0.00"
    if isinstance(value, str):
        value = float(value.replace(",", "").replace("$", "") or 0)
    return f"${value:,.2f}"


def create_account_panel(state, address):
    """Summary panel from /api/hl/clearinghouse response"""
    margin = state.get("marginSummary", {})
    account_value = float(margin.get("accountValue", 0) or 0)
    total_ntl = float(margin.get("totalNtlPos", 0) or 0)
    margin_used = float(margin.get("totalMarginUsed", 0) or 0)
    withdrawable = float(state.get("withdrawable", 0) or 0)
    source = state.get("source", "?")
    open_positions = sum(
        1 for p in state.get("assetPositions", []) if float(p.get("position", {}).get("szi", 0) or 0) != 0
    )

    lines = [
        f"[bold cyan]Wallet:[/bold cyan] [dim]{address[:12]}...{address[-6:]}[/dim]",
        f"[bold cyan]Account Value:[/bold cyan] [yellow]{format_usd(account_value)}[/yellow]",
        f"[bold cyan]Total Position Value:[/bold cyan] [yellow]{format_usd(total_ntl)}[/yellow]",
        f"[bold cyan]Margin Used:[/bold cyan] [yellow]{format_usd(margin_used)}[/yellow]",
        f"[bold cyan]Withdrawable:[/bold cyan] [green]{format_usd(withdrawable)}[/green]",
        f"[bold cyan]Open Positions:[/bold cyan] [white]{open_positions}[/white]",
        f"[bold cyan]Source:[/bold cyan] [magenta]{source}[/magenta] [dim](local node or public fallback)[/dim]",
    ]
    return Panel(
        "\n".join(lines),
        title="📊 [bold white]Clearinghouse[/bold white]  [dim cyan]GET /api/hl/clearinghouse/{address}[/dim cyan]",
        border_style="bright_green",
        box=box.ROUNDED,
        padding=(0, 1),
    )


def create_positions_table(state):
    """Open positions from /api/hl/clearinghouse response"""
    table = Table(
        title="Open Positions",
        box=box.ROUNDED,
        header_style="bold magenta",
        border_style="cyan",
        title_style="bold yellow",
        padding=(0, 1),
    )
    table.add_column("Coin", style="bold white", justify="center")
    table.add_column("Side", justify="center")
    table.add_column("Size", style="cyan", justify="right")
    table.add_column("Entry", justify="right")
    table.add_column("Liq Price", style="red", justify="right")
    table.add_column("Leverage", style="magenta", justify="center")
    table.add_column("uPnL", justify="right")

    rows = 0
    for pos in state.get("assetPositions", []):
        p = pos.get("position", {})
        size = float(p.get("szi", 0) or 0)
        if size == 0:
            continue
        rows += 1
        is_long = size > 0
        side = Text("LONG", style="bold green") if is_long else Text("SHORT", style="bold red")
        pnl = float(p.get("unrealizedPnl", 0) or 0)
        pnl_text = Text(f"{'+' if pnl >= 0 else ''}{format_usd(pnl)}", style="bold green" if pnl >= 0 else "bold red")
        liq = float(p.get("liquidationPx", 0) or 0)
        lev = p.get("leverage", {}).get("value", 0) if isinstance(p.get("leverage"), dict) else 0
        table.add_row(
            p.get("coin", "?"),
            side,
            f"{abs(size):,.4f}",
            f"${float(p.get('entryPx', 0) or 0):,.2f}",
            f"${liq:,.2f}" if liq > 0 else "N/A",
            f"{lev:.0f}x" if lev else "N/A",
            pnl_text,
        )

    if rows == 0:
        table.add_row(Text("Flat - no open positions", style="dim"), "", "", "", "", "", "")
    return table


def create_orders_table(orders_data, coin_filter):
    """Resting orders from /api/hl/open_orders response"""
    title = "Open Orders" + (f"  (filter: {coin_filter})" if coin_filter else "")
    table = Table(
        title=title,
        box=box.ROUNDED,
        header_style="bold magenta",
        border_style="cyan",
        title_style="bold yellow",
        padding=(0, 1),
    )
    table.add_column("Coin", style="bold white", justify="center")
    table.add_column("OID", style="dim", justify="right")
    table.add_column("Side", justify="center")
    table.add_column("Limit Px", justify="right")
    table.add_column("Size", style="cyan", justify="right")
    table.add_column("Type", justify="center")
    table.add_column("TIF", justify="center")
    table.add_column("Reduce", justify="center")

    orders = orders_data.get("orders", [])
    if not orders:
        # 200 with [] means genuinely flat - the signal to skip cancel loops
        table.add_row(Text("No resting orders (skip cancel loop)", style="dim"), "", "", "", "", "", "", "")
        return table

    for o in orders:
        # side: "B" = bid/buy, anything else = ask/sell
        is_buy = o.get("side") == "B"
        side = Text("BUY", style="bold green") if is_buy else Text("SELL", style="bold red")
        table.add_row(
            o.get("coin", "?"),
            str(o.get("oid", "")),
            side,
            f"${float(o.get('limitPx', 0) or 0):,.2f}",
            f"{float(o.get('sz', 0) or 0):,.4f}",
            o.get("orderType", "?"),
            o.get("tif", "?"),
            "yes" if o.get("reduceOnly") else "no",
        )
    return table


def main():
    """Moon Dev: poll clearinghouse + open orders through the direct proxy"""
    console.print(create_banner())

    # Address from CLI or default to the HLP vault (always has data)
    address = sys.argv[1] if len(sys.argv) > 1 else "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"
    coin = sys.argv[2] if len(sys.argv) > 2 else ""

    if len(sys.argv) <= 1:
        console.print(f"[dim]No address provided, using HLP vault: {address[:12]}...[/dim]")
    console.print(f"[bold cyan]Moon Dev: polling {address[:12]}...{address[-6:]}[/bold cyan]\n")

    api = MoonDevAPI()

    # 1) Clearinghouse state (replaces info.user_state)
    state = api.get_hl_clearinghouse(address)
    console.print(create_account_panel(state, address))
    console.print(create_positions_table(state))

    # 2) Open orders (replaces info.open_orders), optional coin filter
    orders_data = api.get_hl_open_orders(address, coin=coin)
    console.print(create_orders_table(orders_data, coin))

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(
        f"\n[dim]Moon Dev | {ts} | source: {state.get('source', '?')} | Hyperliquid Direct-Proxy | moondev.com[/dim]"
    )


if __name__ == "__main__":
    main()
