"""
Moon Dev's OIL Trade Analysis on Hyperliquid HIP-3
Pulling real position and whale data for OIL / Crude Light (CL)

OIL on Hyperliquid HIP-3:
  - xyz:CL = Crude Light (oil futures) - this is where positions live
  - flx:OIL = Oil tick data on flx dex
"""

import sys
import json
sys.path.insert(0, '.')
from api import MoonDevAPI

print("=" * 70)
print("  Moon Dev's OIL HIP-3 Analysis - Hyperliquid Data Layer")
print("  OIL = xyz:CL (Crude Light) on Hyperliquid")
print("=" * 70)

api = MoonDevAPI()

# ============================================================
# 1. OIL PRICE from flx dex tick data
# ============================================================
print("\n" + "=" * 70)
print("  [Moon Dev] STEP 1: Current OIL Price")
print("=" * 70)

ticks = api.get_hip3_ticks("flx", "oil")
oil_price = None
if isinstance(ticks, dict):
    oil_price = ticks.get('latest_price', None)
    print(f"  [Moon Dev] OIL Latest Price: ${oil_price}")
    print(f"  Symbol: {ticks.get('symbol', 'N/A')} | Dex: {ticks.get('dex', 'N/A')} | Display: {ticks.get('display_name', 'N/A')}")
    print(f"  Category: {ticks.get('category', 'N/A')}")
    print(f"  Generated at: {ticks.get('generated_at', 'N/A')}")
    print(f"  Tick count: {ticks.get('tick_count', 'N/A')}")
    tick_list = ticks.get('ticks', [])
    if tick_list:
        print(f"  Last 5 ticks:")
        for t in tick_list[-5:]:
            print(f"    {t.get('datetime', 'N/A')} | ${t.get('price', 'N/A')}")

# Also try xyz CL ticks
print(f"\n  [Moon Dev] Also checking xyz:CL tick data...")
try:
    cl_ticks = api.get_hip3_ticks("xyz", "cl")
    if isinstance(cl_ticks, dict) and 'latest_price' in cl_ticks:
        print(f"  xyz:CL Latest Price: ${cl_ticks.get('latest_price')}")
        print(f"  Generated at: {cl_ticks.get('generated_at', 'N/A')}")
        cl_tick_list = cl_ticks.get('ticks', [])
        if cl_tick_list:
            print(f"  Last 5 ticks:")
            for t in cl_tick_list[-5:]:
                print(f"    {t.get('datetime', 'N/A')} | ${t.get('price', 'N/A')}")
        if not oil_price:
            oil_price = cl_ticks.get('latest_price')
except Exception as e:
    print(f"  xyz:CL ticks error: {e}")

# ============================================================
# 2. ALL POSITIONS for xyz:CL (crude oil)
# ============================================================
print("\n" + "=" * 70)
print("  [Moon Dev] STEP 2: All OIL (xyz:CL) Positions")
print("=" * 70)

all_hip3 = api.get_all_hip3_positions()
oil_data = None
if isinstance(all_hip3, dict) and 'symbols' in all_hip3:
    # Look for CL and any OIL variant
    for sym in all_hip3['symbols']:
        if sym.upper() in ['XYZ:CL', 'FLX:OIL', 'CASH:OIL', 'XYZ:OIL'] or 'OIL' in sym.upper():
            oil_data = all_hip3['symbols'][sym]
            oil_sym = sym
            break
    if not oil_data and 'xyz:CL' in all_hip3['symbols']:
        oil_data = all_hip3['symbols']['xyz:CL']
        oil_sym = 'xyz:CL'

if oil_data:
    longs = oil_data.get('longs', [])
    shorts = oil_data.get('shorts', [])
    print(f"  [Moon Dev] Symbol: {oil_sym}")
    print(f"  Total Longs: {len(longs)} | Total Shorts: {len(shorts)}")

    print(f"\n  --- TOP LONGS (by size) ---")
    sorted_longs = sorted(longs, key=lambda x: float(x.get('size', 0)), reverse=True)
    for i, p in enumerate(sorted_longs[:15]):
        size = p.get('size', 'N/A')
        entry = p.get('entry_price', p.get('entryPx', 'N/A'))
        lev = p.get('leverage', 'N/A')
        liq = p.get('liq_price', p.get('liquidationPx', 'N/A'))
        dist = p.get('distance_to_liq', p.get('dist_to_liq', 'N/A'))
        addr = p.get('address', p.get('user', 'N/A'))
        pnl = p.get('unrealized_pnl', p.get('pnl', 'N/A'))
        print(f"    #{i+1} LONG | Size: ${size} | Entry: ${entry} | Lev: {lev}x | Liq: ${liq} | Dist: {dist} | PnL: {pnl}")
        print(f"         Addr: {addr}")

    print(f"\n  --- TOP SHORTS (by size) ---")
    sorted_shorts = sorted(shorts, key=lambda x: float(x.get('size', 0)), reverse=True)
    for i, p in enumerate(sorted_shorts[:15]):
        size = p.get('size', 'N/A')
        entry = p.get('entry_price', p.get('entryPx', 'N/A'))
        lev = p.get('leverage', 'N/A')
        liq = p.get('liq_price', p.get('liquidationPx', 'N/A'))
        dist = p.get('distance_to_liq', p.get('dist_to_liq', 'N/A'))
        addr = p.get('address', p.get('user', 'N/A'))
        pnl = p.get('unrealized_pnl', p.get('pnl', 'N/A'))
        print(f"    #{i+1} SHORT | Size: ${size} | Entry: ${entry} | Lev: {lev}x | Liq: ${liq} | Dist: {dist} | PnL: {pnl}")
        print(f"          Addr: {addr}")

    # Print raw first long/short for field inspection
    print(f"\n  [Moon Dev] Raw sample LONG fields: {list(longs[0].keys()) if longs else 'none'}")
    if longs:
        print(f"  Raw sample: {json.dumps(longs[0], indent=4)}")
    print(f"\n  [Moon Dev] Raw sample SHORT fields: {list(shorts[0].keys()) if shorts else 'none'}")
    if shorts:
        print(f"  Raw sample: {json.dumps(shorts[0], indent=4)}")
else:
    print("  [Moon Dev] No OIL/CL position data found.")

# ============================================================
# 3. Top HIP-3 positions (near liquidation view)
# ============================================================
print("\n" + "=" * 70)
print("  [Moon Dev] STEP 3: OIL in Top HIP-3 Near-Liquidation Positions")
print("=" * 70)

hip3_top = api.get_hip3_positions()
if isinstance(hip3_top, dict):
    oil_longs = [p for p in hip3_top.get('longs', []) if p.get('coin', '').upper() in ['XYZ:CL'] or 'OIL' in p.get('coin', '').upper()]
    oil_shorts = [p for p in hip3_top.get('shorts', []) if p.get('coin', '').upper() in ['XYZ:CL'] or 'OIL' in p.get('coin', '').upper()]

    print(f"  [Moon Dev] OIL/CL longs near liquidation: {len(oil_longs)}")
    for p in oil_longs:
        print(f"    {p}")

    print(f"  [Moon Dev] OIL/CL shorts near liquidation: {len(oil_shorts)}")
    for p in oil_shorts:
        print(f"    {p}")

    if not oil_longs and not oil_shorts:
        print("  [Moon Dev] No OIL/CL positions in top near-liquidation view (good - means none are close to liq)")

# ============================================================
# 4. Whale activity
# ============================================================
print("\n" + "=" * 70)
print("  [Moon Dev] STEP 4: Whale Activity - OIL/CL Trades")
print("=" * 70)

whales = api.get_whales()
oil_whales = []
if isinstance(whales, dict):
    trades = whales.get('recent_whale_trades', [])
    for w in trades:
        coin = w.get('coin', '')
        if 'OIL' in coin.upper() or coin.upper() == 'XYZ:CL' or coin.upper() == 'CL':
            oil_whales.append(w)
    print(f"  [Moon Dev] Total whale trades in feed: {len(trades)}")
    print(f"  [Moon Dev] OIL/CL whale trades: {len(oil_whales)}")
    for w in oil_whales[:20]:
        print(f"    {w.get('timestamp', 'N/A')} | {w.get('side', 'N/A')} | Size: {w.get('size', 'N/A')} | Price: ${w.get('price', 'N/A')} | Value: ${w.get('value_usd', 'N/A')} | Addr: {w.get('address', 'N/A')}")
    if not oil_whales:
        print("  [Moon Dev] No OIL/CL whale trades in recent feed.")
        hip3_whale_coins = set()
        for w in trades:
            c = w.get('coin', '')
            if ':' in c:
                hip3_whale_coins.add(c)
        print(f"  HIP-3 coins with whale activity: {sorted(hip3_whale_coins)}")
elif isinstance(whales, list):
    for w in whales:
        coin = w.get('coin', '')
        if 'OIL' in coin.upper() or coin.upper() == 'XYZ:CL':
            oil_whales.append(w)
    print(f"  [Moon Dev] Total whale trades: {len(whales)}")
    print(f"  [Moon Dev] OIL/CL whale trades: {len(oil_whales)}")
    for w in oil_whales[:20]:
        print(f"    {w}")

# ============================================================
# 5. Long vs Short Summary
# ============================================================
print("\n" + "=" * 70)
print("  [Moon Dev] STEP 5: OIL Long vs Short Ratio & Bias")
print("=" * 70)

if oil_data:
    longs = oil_data.get('longs', [])
    shorts = oil_data.get('shorts', [])
    num_longs = len(longs)
    num_shorts = len(shorts)
    total = num_longs + num_shorts

    long_size = sum(float(p.get('size', 0)) for p in longs)
    short_size = sum(abs(float(p.get('size', 0))) for p in shorts)
    total_size = long_size + short_size

    print(f"\n  [Moon Dev] OIL ({oil_sym}) Position Summary:")
    print(f"  -----------------------------------------------")
    print(f"  Number of Longs:  {num_longs}")
    print(f"  Number of Shorts: {num_shorts}")
    print(f"  Total Positions:  {total}")
    print(f"  -----------------------------------------------")
    print(f"  Long Size Total:  ${long_size:,.2f}")
    print(f"  Short Size Total: ${short_size:,.2f}")
    print(f"  Combined OI:      ${total_size:,.2f}")
    print(f"  -----------------------------------------------")
    if total_size > 0:
        long_pct = (long_size / total_size) * 100
        short_pct = (short_size / total_size) * 100
        print(f"  Long %:  {long_pct:.1f}%")
        print(f"  Short %: {short_pct:.1f}%")
        if short_size > 0:
            ratio = long_size / short_size
            print(f"  Long/Short Ratio: {ratio:.2f}")
        print(f"  -----------------------------------------------")
        if long_pct > 60:
            print(f"  [Moon Dev] BIAS: STRONGLY LONG ({long_pct:.1f}%)")
        elif long_pct > 50:
            print(f"  [Moon Dev] BIAS: LEAN LONG ({long_pct:.1f}%)")
        elif short_pct > 60:
            print(f"  [Moon Dev] BIAS: STRONGLY SHORT ({short_pct:.1f}%)")
        elif short_pct > 50:
            print(f"  [Moon Dev] BIAS: LEAN SHORT ({short_pct:.1f}%)")
        else:
            print(f"  [Moon Dev] BIAS: NEUTRAL")

    if oil_price:
        print(f"\n  [Moon Dev] Current OIL Price: ${oil_price}")
        # Show distance to liq for each position relative to current price
        print(f"\n  [Moon Dev] Positions closest to liquidation:")
        all_positions = []
        for p in longs:
            liq = p.get('liq_price', p.get('liquidationPx', None))
            if liq:
                dist_pct = abs(float(oil_price) - float(liq)) / float(oil_price) * 100
                all_positions.append(('LONG', p, dist_pct))
        for p in shorts:
            liq = p.get('liq_price', p.get('liquidationPx', None))
            if liq:
                dist_pct = abs(float(oil_price) - float(liq)) / float(oil_price) * 100
                all_positions.append(('SHORT', p, dist_pct))
        all_positions.sort(key=lambda x: x[2])
        for side, p, dist in all_positions[:5]:
            size = p.get('size', 'N/A')
            liq = p.get('liq_price', p.get('liquidationPx', 'N/A'))
            lev = p.get('leverage', 'N/A')
            print(f"    {side} | Size: ${size} | Liq: ${liq} | Distance: {dist:.2f}% | Lev: {lev}x")
else:
    print("  [Moon Dev] No OIL position data to summarize.")

print("\n" + "=" * 70)
print("  [Moon Dev] OIL Analysis Complete")
print("=" * 70)
