"""
Moon Dev's OIL Liquidation Analysis on Hyperliquid HIP-3
Pulling REAL liquidation and market structure data for OIL (CL)

OIL on Hyperliquid HIP-3:
  - xyz:CL = Crude Light (oil futures) - liquidation data
  - flx:OIL = Oil tick data on flx dex
"""

import sys
import json

sys.path.insert(0, '.')
from api import MoonDevAPI

api = MoonDevAPI()

OIL_KEYWORDS = ['CL', 'OIL']

def filter_oil_liqs(liquidations):
    """Filter liquidation events for OIL/CL"""
    results = []
    for x in liquidations:
        coin = x.get('coin', '').upper()
        display = x.get('display_name', '').upper()
        asset = x.get('asset', '').upper()
        if any(kw in [display, asset, coin.split(':')[-1]] for kw in OIL_KEYWORDS):
            results.append(x)
    return results

def print_oil_stats(data, timeframe):
    """Print OIL stats from aggregated data"""
    stats = data.get('stats', {})
    by_asset = stats.get('by_asset', {})
    cl_stats = by_asset.get('CL', by_asset.get('OIL', None))
    if cl_stats:
        print(f"  [Moon Dev] OIL (CL) Aggregated Stats ({timeframe}):")
        print(f"    Total liquidation count: {cl_stats.get('count', 0)}")
        print(f"    Total liq value:  ${cl_stats.get('total_value', 0):,.2f}")
        print(f"    Long liq value:   ${cl_stats.get('long_value', 0):,.2f}")
        print(f"    Short liq value:  ${cl_stats.get('short_value', 0):,.2f}")
        lv = cl_stats.get('long_value', 0)
        sv = cl_stats.get('short_value', 0)
        if lv > sv and sv > 0:
            print(f"    >>> LONGS getting liquidated more ({lv/sv:.1f}x)")
        elif sv > lv and lv > 0:
            print(f"    >>> SHORTS getting liquidated more ({sv/lv:.1f}x)")
        elif sv > 0 and lv == 0:
            print(f"    >>> ALL SHORTS getting liquidated (100% short liqs)")
        elif lv > 0 and sv == 0:
            print(f"    >>> ALL LONGS getting liquidated (100% long liqs)")
        else:
            print(f"    >>> Even liquidation pressure")
    else:
        print(f"  [Moon Dev] No OIL/CL in aggregated stats for {timeframe}")
        if by_asset:
            print(f"    Available assets: {list(by_asset.keys())}")

def print_oil_events(data, timeframe, max_show=20):
    """Print individual OIL liquidation events"""
    liqs = data.get('liquidations', [])
    oil_events = filter_oil_liqs(liqs)
    print(f"  [Moon Dev] Individual OIL liq events ({timeframe}): {len(oil_events)} found")
    for i, ev in enumerate(oil_events[:max_show]):
        side = ev.get('side', '?').upper()
        size = ev.get('size', 0)
        price = ev.get('price', 0)
        val = ev.get('value_usd', 0)
        ts = ev.get('timestamp', '?')
        coin = ev.get('coin', ev.get('display_name', '?'))
        addr = ev.get('liquidated_address', '?')[:14] + '...'
        print(f"    [{i+1:>3}] {side:5s} | {coin} | size={size} | price=${price} | val=${val:,.2f} | {ts[:19]} | {addr}")
    if len(oil_events) > max_show:
        print(f"    ... and {len(oil_events) - max_show} more events")


print("=" * 70)
print("  Moon Dev's OIL (CL) HIP-3 Liquidation Analysis")
print("  Hyperliquid Data Layer API - REAL DATA")
print("=" * 70)

# ============================================================
# 1h liquidations
# ============================================================
print("\n" + "=" * 70)
print("  [Moon Dev] HIP-3 Liquidations - 1h (OIL/CL)")
print("=" * 70)
data_1h = api.get_hip3_liquidations('1h')
print(f"  Data timestamp: {data_1h.get('updated_at', 'N/A')}")
print_oil_stats(data_1h, '1h')
print_oil_events(data_1h, '1h')

# ============================================================
# 24h liquidations
# ============================================================
print("\n" + "=" * 70)
print("  [Moon Dev] HIP-3 Liquidations - 24h (OIL/CL)")
print("=" * 70)
data_24h = api.get_hip3_liquidations('24h')
print(f"  Data timestamp: {data_24h.get('updated_at', 'N/A')}")
print_oil_stats(data_24h, '24h')
print_oil_events(data_24h, '24h')

# ============================================================
# 7d liquidations
# ============================================================
print("\n" + "=" * 70)
print("  [Moon Dev] HIP-3 Liquidations - 7d (OIL/CL)")
print("=" * 70)
data_7d = api.get_hip3_liquidations('7d')
print(f"  Data timestamp: {data_7d.get('updated_at', 'N/A')}")
print_oil_stats(data_7d, '7d')
print_oil_events(data_7d, '7d', max_show=30)

# ============================================================
# Summary table across timeframes
# ============================================================
print("\n" + "-" * 70)
print("  [Moon Dev] OIL Liquidation Summary Across Timeframes")
print("-" * 70)
for label, data in [('1h', data_1h), ('24h', data_24h), ('7d', data_7d)]:
    by_asset = data.get('stats', {}).get('by_asset', {})
    cl = by_asset.get('CL', by_asset.get('OIL', {}))
    liqs = data.get('liquidations', [])
    oil_events = filter_oil_liqs(liqs)
    long_events = [e for e in oil_events if e.get('side') == 'long']
    short_events = [e for e in oil_events if e.get('side') == 'short']
    print(f"  {label:>4s}: count={cl.get('count', 0):>5} | "
          f"total=${cl.get('total_value', 0):>12,.2f} | "
          f"longs=${cl.get('long_value', 0):>10,.2f} | "
          f"shorts=${cl.get('short_value', 0):>10,.2f} | "
          f"events: {len(long_events)}L/{len(short_events)}S")

# ============================================================
# Liquidation Stats endpoint
# ============================================================
print("\n" + "=" * 70)
print("  [Moon Dev] HIP-3 Liquidation Stats (OIL/CL)")
print("=" * 70)
stats = api.get_hip3_liquidation_stats()
if isinstance(stats, dict):
    print(f"  [Moon Dev] Overall HIP-3 Liquidation Stats:")
    for key in ['total_count', 'total_volume', 'long_count', 'short_count', 'long_volume', 'short_volume']:
        if key in stats:
            val = stats[key]
            if isinstance(val, float) and ('volume' in key or 'value' in key):
                print(f"    {key}: ${val:,.2f}")
            else:
                print(f"    {key}: {val}")

    # Look for OIL in by_symbol or by_asset
    by_symbol = stats.get('by_symbol', stats.get('by_asset', {}))
    found_oil = False
    if isinstance(by_symbol, dict):
        for sym_key in by_symbol:
            if sym_key.upper() in OIL_KEYWORDS or 'CL' == sym_key.upper():
                found_oil = True
                print(f"\n  [Moon Dev] OIL Stats from stats['{sym_key}']:")
                print(f"  {json.dumps(by_symbol[sym_key], indent=4)}")
    elif isinstance(by_symbol, list):
        for item in by_symbol:
            if isinstance(item, dict) and any(s in str(item).upper() for s in OIL_KEYWORDS):
                found_oil = True
                print(f"\n  [Moon Dev] OIL found in stats:")
                print(f"  {json.dumps(item, indent=4)}")

    top = stats.get('top_symbols', [])
    if top:
        print(f"\n  [Moon Dev] Top symbols by liq volume:")
        for t in top[:10]:
            marker = " <<<< OIL" if any(s in str(t).upper() for s in OIL_KEYWORDS) else ""
            print(f"    {t}{marker}")

    by_cat = stats.get('by_category', {})
    if isinstance(by_cat, dict) and 'commodities' in by_cat:
        print(f"\n  [Moon Dev] Commodities Category:")
        print(f"  {json.dumps(by_cat['commodities'], indent=4)}")

    if not found_oil:
        print(f"\n  [Moon Dev] Full stats dump (OIL/CL not found separately):")
        print(f"  {json.dumps(stats, indent=2)[:3000]}")
else:
    print(f"  [Moon Dev] Raw stats: {json.dumps(stats, indent=2)[:2000]}")

# ============================================================
# Tick Data - OIL price action
# ============================================================
print("\n" + "=" * 70)
print("  [Moon Dev] OIL Tick/Price Data")
print("=" * 70)

for dex, ticker in [('flx', 'oil'), ('xyz', 'cl')]:
    print(f"\n  --- [Moon Dev] Fetching {dex}:{ticker} ---")
    tick_data = api.get_hip3_ticks(dex, ticker)
    if isinstance(tick_data, dict):
        latest = tick_data.get('latest_price', None)
        if latest:
            print(f"  Latest Price: ${latest}")
        print(f"  Symbol: {tick_data.get('symbol', 'N/A')} | Dex: {tick_data.get('dex', 'N/A')}")
        print(f"  Category: {tick_data.get('category', 'N/A')}")
        print(f"  Generated: {tick_data.get('generated_at', 'N/A')}")
        print(f"  Tick count: {tick_data.get('tick_count', 'N/A')}")
        tick_list = tick_data.get('ticks', [])
        if tick_list:
            print(f"\n  Last 10 ticks:")
            for t in tick_list[-10:]:
                print(f"    {t.get('datetime', t.get('timestamp', 'N/A'))} | ${t.get('price', 'N/A')}")

            # Extract prices for trend
            prices = [float(t['price']) for t in tick_list if 'price' in t]
            if prices:
                print(f"\n  [Moon Dev] OIL Price Summary ({dex}:{ticker}):")
                print(f"    Ticks: {len(prices)}")
                print(f"    First: ${prices[0]:,.4f}")
                print(f"    Last:  ${prices[-1]:,.4f}")
                print(f"    High:  ${max(prices):,.4f}")
                print(f"    Low:   ${min(prices):,.4f}")
                pct = ((prices[-1] - prices[0]) / prices[0]) * 100 if prices[0] != 0 else 0
                print(f"    Change: {pct:+.2f}%")
                if pct > 0.5:
                    print(f"    [Moon Dev] Trend: BULLISH (up {pct:.2f}%)")
                elif pct < -0.5:
                    print(f"    [Moon Dev] Trend: BEARISH (down {abs(pct):.2f}%)")
                else:
                    print(f"    [Moon Dev] Trend: SIDEWAYS")
                if len(prices) >= 5:
                    recent = prices[-5:]
                    print(f"    Recent 5: {['${:,.2f}'.format(p) for p in recent]}")
                    micro = ((recent[-1] - recent[0]) / recent[0]) * 100
                    print(f"    Micro-trend (last 5): {micro:+.2f}%")
    elif isinstance(tick_data, list) and len(tick_data) > 0:
        print(f"  Got {len(tick_data)} ticks (list format)")
        for t in tick_data[-10:]:
            print(f"    {t}")
    else:
        print(f"  [Moon Dev] {dex}:{ticker}: {str(tick_data)[:300]}")

print("\n" + "=" * 70)
print("  Moon Dev's OIL (CL) Liquidation Analysis Complete!")
print("  All data pulled LIVE from Hyperliquid Data Layer API")
print("=" * 70)
