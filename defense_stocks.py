"""
Moon Dev's Defense/Missile Stock Scanner for Hyperliquid HIP-3
Searching for LMT, RTX, BA, NOC, GD and other defense/aerospace tickers
"""
import sys
import json
sys.path.insert(0, '.')
from api import MoonDevAPI

api = MoonDevAPI()

DEFENSE_KEYWORDS = ['lmt', 'lockheed', 'rtx', 'raytheon', 'ba', 'boeing', 'noc', 'northrop',
                    'gd', 'general dynamics', 'lhx', 'l3harris', 'defense', 'missile']

def is_defense(symbol_str):
    s = symbol_str.lower()
    return any(k in s for k in DEFENSE_KEYWORDS)

print("=" * 70)
print("  Moon Dev's Defense/Missile Stock Scanner - Hyperliquid HIP-3")
print("=" * 70)

# 1. Get HIP-3 tick stats (all symbols and prices)
print("\n[Moon Dev] Fetching HIP-3 tick stats...")
tick_stats = api.get_hip3_tick_stats()

# Print latest prices for all symbols
if isinstance(tick_stats, dict) and 'latest_prices' in tick_stats:
    print(f"\n[Moon Dev] === ALL HIP-3 LATEST PRICES ({len(tick_stats['latest_prices'])} symbols) ===")
    for sym, price in sorted(tick_stats['latest_prices'].items()):
        defense_tag = " *** DEFENSE ***" if is_defense(sym) else ""
        print(f"    {sym:30s} ${price}{defense_tag}")

if isinstance(tick_stats, dict) and 'symbols' in tick_stats:
    print(f"\n[Moon Dev] === ALL HIP-3 TRACKED SYMBOLS ({len(tick_stats['symbols'])}) ===")
    for sym in sorted(tick_stats['symbols']):
        defense_tag = " *** DEFENSE ***" if is_defense(sym) else ""
        print(f"    {sym}{defense_tag}")

if isinstance(tick_stats, dict) and 'categories' in tick_stats:
    print(f"\n[Moon Dev] === CATEGORIES ===")
    cats = tick_stats['categories']
    if isinstance(cats, dict):
        for cat, info in cats.items():
            print(f"    {cat}: {info}")
    elif isinstance(cats, list):
        for c in cats:
            print(f"    {c}")

# 2. Get HIP-3 meta (all symbols with prices)
print("\n[Moon Dev] Fetching HIP-3 meta (all symbols + prices)...")
meta = api.get_hip3_meta(include_delisted=True)

all_stock_symbols = []
if isinstance(meta, dict):
    print(f"[Moon Dev] Total HIP-3 symbols: {meta.get('total_symbols', meta.get('count', 'N/A'))}")

    # dexes is a list
    if 'dexes' in meta and isinstance(meta['dexes'], list):
        print(f"\n[Moon Dev] Dexes available: {meta['dexes']}")

    if 'dex_summary' in meta:
        print(f"\n[Moon Dev] === DEX SUMMARY ===")
        ds = meta['dex_summary']
        if isinstance(ds, dict):
            for dex, info in ds.items():
                print(f"    {dex}: {info}")
        elif isinstance(ds, list):
            for item in ds:
                print(f"    {item}")

    # Print all symbols
    if 'symbols' in meta and isinstance(meta['symbols'], list):
        print(f"\n[Moon Dev] === ALL HIP-3 SYMBOLS FROM META ({len(meta['symbols'])}) ===")
        for s in sorted(meta['symbols'], key=lambda x: str(x.get('symbol', x.get('ticker', ''))) if isinstance(x, dict) else str(x)):
            if isinstance(s, dict):
                sym = s.get('symbol', s.get('ticker', ''))
                price = s.get('price', s.get('mark_price', s.get('mid', 'N/A')))
                cat = s.get('category', '')
                dex = s.get('dex', '')
                delisted = s.get('delisted', False)
                status = " [DELISTED]" if delisted else ""
                defense_tag = " *** DEFENSE ***" if is_defense(str(sym)) else ""
                print(f"    {str(sym):25s} dex: {str(dex):6s} price: {str(price):>12s}  cat: {str(cat):12s}{status}{defense_tag}")
                if cat in ('stocks', 'stock') or 'stock' in str(cat).lower():
                    all_stock_symbols.append(s)
            else:
                print(f"    {s}")

# Search for defense stocks
print("\n" + "=" * 70)
print("[Moon Dev] SEARCHING FOR DEFENSE/AEROSPACE STOCKS...")
print("=" * 70)

defense_found = []
if isinstance(meta, dict) and 'symbols' in meta and isinstance(meta['symbols'], list):
    for s in meta['symbols']:
        if isinstance(s, dict):
            sym = str(s.get('symbol', s.get('ticker', '')))
            if is_defense(sym):
                defense_found.append(s)
                print(f"\n  [Moon Dev] DEFENSE STOCK FOUND: {sym}")
                for k, v in s.items():
                    print(f"      {k}: {v}")

# Also check tick_stats symbols
if isinstance(tick_stats, dict):
    for key in ['symbols', 'latest_prices']:
        if key in tick_stats:
            items = tick_stats[key] if isinstance(tick_stats[key], list) else list(tick_stats[key].keys()) if isinstance(tick_stats[key], dict) else []
            for sym in items:
                if is_defense(str(sym)) and str(sym) not in [str(d.get('symbol', d)) for d in defense_found]:
                    defense_found.append({'symbol': sym, 'source': 'tick_stats'})
                    print(f"\n  [Moon Dev] DEFENSE STOCK FOUND in tick_stats: {sym}")

if not defense_found:
    print("[Moon Dev] No defense stocks (LMT, RTX, BA, NOC, GD) found in HIP-3.")

# 3. Get ALL HIP-3 positions
print("\n" + "=" * 70)
print("[Moon Dev] Fetching ALL HIP-3 positions...")
print("=" * 70)
positions = api.get_all_hip3_positions()

if isinstance(positions, dict) and 'symbols' in positions:
    print(f"[Moon Dev] Total HIP-3 symbols with positions: {positions.get('total_symbols', len(positions['symbols']))}")
    print(f"\n[Moon Dev] === ALL HIP-3 POSITION SYMBOLS ===")
    for sym_key in sorted(positions['symbols'].keys()):
        sym_data = positions['symbols'][sym_key]
        summary = ""
        if isinstance(sym_data, dict):
            longs = sym_data.get('longs', [])
            shorts = sym_data.get('shorts', [])
            long_count = len(longs) if isinstance(longs, list) else 0
            short_count = len(shorts) if isinstance(shorts, list) else 0
            summary = f"  longs: {long_count}, shorts: {short_count}"
        defense_tag = " *** DEFENSE ***" if is_defense(sym_key) else ""
        print(f"    {sym_key:30s}{summary}{defense_tag}")

        # Show defense details
        if is_defense(sym_key) and isinstance(sym_data, dict):
            print(f"\n    *** [Moon Dev] DEFENSE STOCK POSITIONING: {sym_key} ***")
            for key, val in sym_data.items():
                if key not in ('longs', 'shorts'):
                    print(f"        {key}: {val}")
            for side in ['longs', 'shorts']:
                entries = sym_data.get(side, [])
                if isinstance(entries, list) and entries:
                    print(f"        Top {side} (showing up to 5):")
                    for e in entries[:5]:
                        if isinstance(e, dict):
                            addr = e.get('address', e.get('user', ''))[:12] + '...'
                            size = e.get('size', e.get('position_value', e.get('notional', 'N/A')))
                            entry = e.get('entry_price', e.get('entryPx', 'N/A'))
                            print(f"          {addr}  size: {size}  entry: {entry}")
                        else:
                            print(f"          {e}")

# 4. Get HIP-3 liquidation stats
print("\n" + "=" * 70)
print("[Moon Dev] Fetching HIP-3 liquidation stats...")
print("=" * 70)
liq_stats = api.get_hip3_liquidation_stats()

if isinstance(liq_stats, dict):
    print(f"[Moon Dev] Total liquidations: {liq_stats.get('total_count', 'N/A')}")
    print(f"[Moon Dev] Total volume: ${liq_stats.get('total_volume', 'N/A')}")
    print(f"[Moon Dev] Long liqs: {liq_stats.get('long_count', 'N/A')} (${liq_stats.get('long_volume', 'N/A')})")
    print(f"[Moon Dev] Short liqs: {liq_stats.get('short_count', 'N/A')} (${liq_stats.get('short_volume', 'N/A')})")

    if 'by_symbol' in liq_stats:
        print(f"\n[Moon Dev] === LIQUIDATIONS BY SYMBOL ===")
        by_sym = liq_stats['by_symbol']
        if isinstance(by_sym, dict):
            for sym, data in sorted(by_sym.items()):
                defense_tag = " *** DEFENSE ***" if is_defense(sym) else ""
                print(f"    {sym:30s} {data}{defense_tag}")
        elif isinstance(by_sym, list):
            for item in by_sym:
                print(f"    {item}")

    if 'top_symbols' in liq_stats:
        print(f"\n[Moon Dev] === TOP SYMBOLS BY LIQUIDATION ===")
        top = liq_stats['top_symbols']
        if isinstance(top, list):
            for item in top:
                print(f"    {item}")
        elif isinstance(top, dict):
            for sym, data in top.items():
                print(f"    {sym}: {data}")

    if 'by_category' in liq_stats:
        print(f"\n[Moon Dev] === LIQUIDATIONS BY CATEGORY ===")
        by_cat = liq_stats['by_category']
        if isinstance(by_cat, dict):
            for cat, data in by_cat.items():
                print(f"    {cat}: {data}")

# Final summary
print("\n" + "=" * 70)
print("[Moon Dev] FINAL SUMMARY")
print("=" * 70)
if defense_found:
    print(f"[Moon Dev] Found {len(defense_found)} defense/aerospace stocks on HIP-3!")
    for s in defense_found:
        print(f"  -> {s}")
else:
    print("[Moon Dev] No defense/missile stocks (LMT, RTX, BA, NOC, GD, LHX) are listed on Hyperliquid HIP-3.")
    print("[Moon Dev] HIP-3 currently has stocks like TSLA, NVDA, AAPL, AMZN, META, GOOG, etc.")
    print("[Moon Dev] Defense tickers (Lockheed Martin, Raytheon) are NOT available for trading on HIP-3.")

print("\n[Moon Dev] Scan complete.")
