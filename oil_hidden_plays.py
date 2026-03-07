"""
Moon Dev's Oil Run-Up Hidden Opportunity Scanner
Finds correlated plays, squeeze candidates, and hidden moves on HIP-3
"""
import sys
sys.path.insert(0, '.')
from api import MoonDevAPI
import json

api = MoonDevAPI()

print("=" * 80)
print("  Moon Dev's HIP-3 Hidden Opportunity Scanner")
print("  Oil ran up big - what else is moving? Where are the hidden plays?")
print("=" * 80)

# ============================================================
# 1. GET HIP-3 META (all prices + categories)
# ============================================================
print("\n[Moon Dev] Fetching HIP-3 meta (all assets + prices)...")
meta = api.get_hip3_meta()

# Debug: understand structure
# The symbols list has objects - let's see what keys they have
symbols_list = meta.get('symbols', [])
if symbols_list:
    print(f"\n[Moon Dev] Sample symbol keys: {list(symbols_list[0].keys())}")
    print(f"[Moon Dev] Sample symbol: {json.dumps(symbols_list[0], default=str)}")

# Also check categories structure
cats_raw = meta.get('categories', {})
print(f"\n[Moon Dev] Categories keys: {list(cats_raw.keys()) if isinstance(cats_raw, dict) else type(cats_raw)}")
if isinstance(cats_raw, dict) and cats_raw:
    first_cat = list(cats_raw.keys())[0]
    cat_val = cats_raw[first_cat]
    if isinstance(cat_val, list) and cat_val:
        print(f"[Moon Dev] Sample from '{first_cat}': {json.dumps(cat_val[0], default=str)}")

# Build a lookup: figure out the ticker/name field
def get_ticker(s):
    return s.get('ticker', s.get('symbol', s.get('name', s.get('coin', '?'))))

def get_price(s):
    return s.get('price', s.get('mark_price', s.get('mid', s.get('markPx', '?'))))

def get_dex(s):
    return s.get('dex', s.get('prefix', '?'))

def get_category(s):
    return s.get('category', s.get('type', 'unknown'))

# ============================================================
# PRICE DASHBOARD
# ============================================================
print(f"\n{'='*80}")
print(f"  Moon Dev's HIP-3 PRICE DASHBOARD - {len(symbols_list)} symbols")
print(f"{'='*80}")

# Group by category
categories = {}
all_sym_map = {}
for s in symbols_list:
    cat = get_category(s)
    categories.setdefault(cat, []).append(s)
    key = f"{get_dex(s)}:{get_ticker(s)}"
    all_sym_map[key] = s

for cat in sorted(categories.keys()):
    syms = categories[cat]
    print(f"\n--- {cat.upper()} ---")
    for s in sorted(syms, key=lambda x: get_ticker(x)):
        ticker = get_ticker(s)
        price = get_price(s)
        dex = get_dex(s)
        print(f"  {dex}:{ticker:12s}  price: {price}")

# ============================================================
# 2. TICK STATS
# ============================================================
print(f"\n{'='*80}")
print("  Moon Dev's HIP-3 Tick Stats Overview")
print(f"{'='*80}")
tick_stats = api.get_hip3_tick_stats()
# Print summary
for key in ['generated_at', 'market_type', 'collection_method', 'total_symbols', 'total_ticks']:
    if key in tick_stats:
        print(f"  {key}: {tick_stats[key]}")
if 'dex_counts' in tick_stats:
    print(f"  dex_counts: {tick_stats['dex_counts']}")
if 'symbols' in tick_stats:
    print(f"  tracked symbols: {tick_stats['symbols']}")

# ============================================================
# 3. ALL HIP-3 POSITIONS
# ============================================================
print(f"\n{'='*80}")
print("  Moon Dev's HIP-3 POSITIONING ANALYSIS - Finding Squeeze Candidates")
print(f"{'='*80}")

positions = api.get_all_hip3_positions()

# Debug: check structure
if isinstance(positions, dict):
    top_keys = list(positions.keys())
    print(f"\n[Moon Dev] Position data keys: {top_keys}")
    if 'symbols' in positions:
        sym_keys = list(positions['symbols'].keys())[:5]
        print(f"[Moon Dev] Sample symbol keys: {sym_keys}")
        if sym_keys:
            sample = positions['symbols'][sym_keys[0]]
            if isinstance(sample, dict):
                print(f"[Moon Dev] Sample structure for {sym_keys[0]}: {list(sample.keys())}")
                # Check what a position entry looks like
                for side_key in ['longs', 'shorts', 'long', 'short', 'positions']:
                    if side_key in sample and sample[side_key]:
                        items = sample[side_key]
                        if isinstance(items, list) and items:
                            print(f"[Moon Dev] Sample {side_key}[0] keys: {list(items[0].keys())}")
                            print(f"[Moon Dev] Sample {side_key}[0]: {json.dumps(items[0], default=str)[:500]}")
                            break

position_data = []
if isinstance(positions, dict) and 'symbols' in positions:
    for symbol, data in positions['symbols'].items():
        if not isinstance(data, dict):
            continue

        longs = data.get('longs', data.get('long', []))
        shorts = data.get('shorts', data.get('short', []))
        if not isinstance(longs, list): longs = []
        if not isinstance(shorts, list): shorts = []

        def get_value(p):
            for key in ['position_value', 'size_usd', 'notional', 'value', 'szi', 'positionValue']:
                if key in p:
                    v = p[key]
                    if isinstance(v, str):
                        v = float(v) if v else 0
                    return abs(float(v))
            return 0

        long_value = sum(get_value(p) for p in longs)
        short_value = sum(get_value(p) for p in shorts)
        total = long_value + short_value

        if total > 0:
            long_pct = long_value / total * 100
            short_pct = short_value / total * 100
            skew = abs(long_pct - 50)

            position_data.append({
                'symbol': symbol,
                'long_count': len(longs),
                'short_count': len(shorts),
                'long_value': long_value,
                'short_value': short_value,
                'total_value': total,
                'long_pct': long_pct,
                'short_pct': short_pct,
                'skew': skew,
                'direction': 'LONG-HEAVY' if long_pct > 50 else 'SHORT-HEAVY'
            })

position_data.sort(key=lambda x: x['skew'], reverse=True)

print(f"\n[Moon Dev] {len(position_data)} HIP-3 assets with open positions")
print(f"\n{'Symbol':<25} {'#L':>4} {'#S':>4} {'Long$':>12} {'Short$':>12} {'L%':>6} {'S%':>6} {'Skew':>6} {'Direction'}")
print("-" * 105)
for p in position_data:
    print(f"{p['symbol']:<25} {p['long_count']:>4} {p['short_count']:>4} ${p['long_value']:>10,.0f} ${p['short_value']:>10,.0f} {p['long_pct']:>5.1f}% {p['short_pct']:>5.1f}% {p['skew']:>5.1f} {p['direction']}")

# ============================================================
# 4. SQUEEZE CANDIDATES
# ============================================================
print(f"\n{'='*80}")
print("  Moon Dev's TOP SQUEEZE CANDIDATES (most one-sided positioning)")
print(f"{'='*80}")

for i, p in enumerate(position_data[:15]):
    if p['long_pct'] > 60:
        direction = "SHORT SQUEEZE potential (crowded long -> could squeeze shorts further)"
    elif p['short_pct'] > 60:
        direction = "LONG SQUEEZE risk (crowded short -> shorts could get squeezed!)"
    else:
        direction = "relatively balanced"
    print(f"\n  #{i+1} {p['symbol']}")
    print(f"      Long: {p['long_pct']:.1f}% (${p['long_value']:,.0f})  |  Short: {p['short_pct']:.1f}% (${p['short_value']:,.0f})")
    print(f"      Skew: {p['skew']:.1f}%  ->  {direction}")

# ============================================================
# 5. HIP-3 LIQUIDATION STATS
# ============================================================
print(f"\n{'='*80}")
print("  Moon Dev's HIP-3 LIQUIDATION STATS (aggregate)")
print(f"{'='*80}")

liq_stats = api.get_hip3_liquidation_stats()
# Print top-level stats
for key in ['total_count', 'total_volume', 'long_count', 'short_count', 'long_volume', 'short_volume', 'updated_at']:
    if key in liq_stats:
        val = liq_stats[key]
        if isinstance(val, (int, float)) and val > 1000:
            print(f"  {key}: ${val:,.2f}" if 'volume' in key or 'value' in key else f"  {key}: {val:,}")
        else:
            print(f"  {key}: {val}")

# by_category
if 'by_category' in liq_stats:
    print("\n  By Category:")
    for cat, cdata in liq_stats['by_category'].items():
        if isinstance(cdata, dict):
            print(f"    {cat}: {json.dumps(cdata, default=str)}")
        else:
            print(f"    {cat}: {cdata}")

# by_symbol / top_symbols
for key in ['top_symbols', 'by_symbol']:
    if key in liq_stats:
        print(f"\n  {key}:")
        val = liq_stats[key]
        if isinstance(val, dict):
            sorted_syms = sorted(val.items(), key=lambda x: x[1].get('total_value', 0) if isinstance(x[1], dict) else 0, reverse=True)
            for sym, sdata in sorted_syms[:20]:
                print(f"    {sym}: {json.dumps(sdata, default=str)}")
        elif isinstance(val, list):
            for item in val[:20]:
                print(f"    {json.dumps(item, default=str)}")

# ============================================================
# 6. 24H LIQUIDATIONS
# ============================================================
print(f"\n{'='*80}")
print("  Moon Dev's HIP-3 24H LIQUIDATION ACTIVITY")
print(f"{'='*80}")

liqs_24h = api.get_hip3_liquidations('24h')

liq_by_symbol = {}
liq_symbols_set = set()

if isinstance(liqs_24h, list):
    print(f"\n[Moon Dev] {len(liqs_24h)} liquidation events in 24h")
    if liqs_24h:
        print(f"[Moon Dev] Sample liq keys: {list(liqs_24h[0].keys())}")

    for liq in liqs_24h:
        sym = liq.get('symbol', liq.get('coin', liq.get('asset', '?')))
        liq_symbols_set.add(sym)
        if sym not in liq_by_symbol:
            liq_by_symbol[sym] = {'count': 0, 'total_value': 0, 'long_liqs': 0, 'short_liqs': 0, 'long_val': 0, 'short_val': 0}
        liq_by_symbol[sym]['count'] += 1
        val = 0
        for vk in ['value_usd', 'size_usd', 'notional', 'value']:
            if vk in liq:
                val = abs(float(liq[vk]))
                break
        liq_by_symbol[sym]['total_value'] += val
        side = str(liq.get('side', '')).lower()
        if 'long' in side:
            liq_by_symbol[sym]['long_liqs'] += 1
            liq_by_symbol[sym]['long_val'] += val
        elif 'short' in side:
            liq_by_symbol[sym]['short_liqs'] += 1
            liq_by_symbol[sym]['short_val'] += val

    sorted_liqs = sorted(liq_by_symbol.items(), key=lambda x: x[1]['total_value'], reverse=True)
    print(f"\n{'Symbol':<20} {'Count':>8} {'Value':>14} {'LongLiqs':>10} {'ShortLiqs':>10} {'LongVal':>12} {'ShortVal':>12}")
    print("-" * 90)
    for sym, d in sorted_liqs:
        print(f"{sym:<20} {d['count']:>8} ${d['total_value']:>12,.0f} {d['long_liqs']:>10} {d['short_liqs']:>10} ${d['long_val']:>10,.0f} ${d['short_val']:>10,.0f}")

elif isinstance(liqs_24h, dict):
    print(f"\n[Moon Dev] 24h liq data is dict with keys: {list(liqs_24h.keys())}")

    # Check if it has stats.by_asset structure
    stats = liqs_24h.get('stats', liqs_24h)
    by_asset = stats.get('by_asset', stats.get('by_symbol', {}))

    if by_asset:
        print(f"\n[Moon Dev] Found {len(by_asset)} assets with liquidation data")
        total_info = {k: v for k, v in stats.items() if k not in ['by_asset', 'by_symbol']}
        for k, v in total_info.items():
            if isinstance(v, (int, float)) and v > 1000:
                print(f"  {k}: ${v:,.2f}" if 'value' in k or 'volume' in k else f"  {k}: {v:,}")
            else:
                print(f"  {k}: {v}")

        sorted_assets = sorted(by_asset.items(), key=lambda x: x[1].get('total_value', 0) if isinstance(x[1], dict) else 0, reverse=True)
        print(f"\n{'Symbol':<20} {'Count':>8} {'Total Value':>14} {'Long Val':>14} {'Short Val':>14}")
        print("-" * 75)
        for sym, d in sorted_assets:
            liq_symbols_set.add(sym)
            if isinstance(d, dict):
                liq_by_symbol[sym] = d
                cnt = d.get('count', 0)
                tv = d.get('total_value', 0)
                lv = d.get('long_value', 0)
                sv = d.get('short_value', 0)
                print(f"{sym:<20} {cnt:>8} ${tv:>12,.0f} ${lv:>12,.0f} ${sv:>12,.0f}")
    else:
        print(json.dumps(liqs_24h, indent=2, default=str)[:4000])

# ============================================================
# 7. COMMODITY FOCUS
# ============================================================
print(f"\n{'='*80}")
print("  Moon Dev's COMMODITY CORRELATION ANALYSIS")
print("  Oil ran up - what else in commodities is moving?")
print(f"{'='*80}")

commodity_keywords = ['GOLD', 'SILVER', 'OIL', 'CL', 'NATGAS', 'COPPER', 'URANIUM']
found_commodities = []
for cat_name, syms in categories.items():
    if 'commod' in cat_name.lower():
        for s in syms:
            ticker = get_ticker(s)
            price = get_price(s)
            dex = get_dex(s)
            full = f"{dex}:{ticker}"
            print(f"\n  {full:20s} -> price: {price}")
            found_commodities.append(full)
            for p in position_data:
                if ticker.upper() in p['symbol'].upper():
                    print(f"    Positioning: {p['long_pct']:.1f}% long / {p['short_pct']:.1f}% short | Skew: {p['skew']:.1f}% {p['direction']}")
                    if p['symbol'].split(':')[-1] in liq_by_symbol or p['symbol'] in liq_by_symbol:
                        sym_key = p['symbol'].split(':')[-1] if p['symbol'].split(':')[-1] in liq_by_symbol else p['symbol']
                        ld = liq_by_symbol.get(sym_key, {})
                        if isinstance(ld, dict):
                            print(f"    24h Liqs: count={ld.get('count', 0)}, value=${ld.get('total_value', 0):,.0f}")

# Also check by keyword if no category matched
if not found_commodities:
    print("  [Moon Dev] No 'commodities' category found. Searching by keyword...")
    for key, s in all_sym_map.items():
        ticker = get_ticker(s)
        for kw in commodity_keywords:
            if kw.upper() in ticker.upper() or kw.upper() in key.upper():
                print(f"  {key:20s} -> price: {get_price(s)}")

# ============================================================
# 8. ALL XYZ AND FLX TICKERS
# ============================================================
print(f"\n{'='*80}")
print("  Moon Dev's XYZ + FLX DEX BREAKDOWN (all stocks/commodities)")
print(f"{'='*80}")

for dex_prefix in ['xyz', 'flx', 'km', 'vntl']:
    dex_syms = [(k, v) for k, v in all_sym_map.items() if k.startswith(f"{dex_prefix}:")]
    if dex_syms:
        print(f"\n  [{dex_prefix.upper()} DEX] {len(dex_syms)} symbols:")
        for key, s in sorted(dex_syms):
            ticker = get_ticker(s)
            price = get_price(s)
            cat = get_category(s)
            line = f"    {key:20s}  price: {str(price):>12s}  cat: {cat}"
            # add positioning if available
            for p in position_data:
                if p['symbol'] == key or ticker.upper() in p['symbol'].upper():
                    line += f"  | L:{p['long_pct']:.0f}% S:{p['short_pct']:.0f}% skew:{p['skew']:.0f}"
                    break
            print(line)

# ============================================================
# 9. MACRO CONTEXT (indices)
# ============================================================
print(f"\n{'='*80}")
print("  Moon Dev's MACRO CONTEXT (Indices)")
print(f"{'='*80}")

index_keywords = ['US500', 'USTECH', 'SMALL2000', 'XYZ100', 'INDEX', 'SP500', 'NDX', 'RUT']
for cat_name, syms in categories.items():
    if 'indic' in cat_name.lower() or 'index' in cat_name.lower():
        for s in syms:
            ticker = get_ticker(s)
            price = get_price(s)
            dex = get_dex(s)
            full = f"{dex}:{ticker}"
            print(f"\n  {full:20s} -> price: {price}")
            for p in position_data:
                if ticker.upper() in p['symbol'].upper():
                    print(f"    Positioning: {p['long_pct']:.1f}% long / {p['short_pct']:.1f}% short | Skew: {p['skew']:.1f}% {p['direction']}")

# ============================================================
# 10. FINAL ANALYSIS
# ============================================================
print(f"\n{'='*80}")
print("  Moon Dev's HIDDEN OPPORTUNITY SUMMARY")
print(f"{'='*80}")

print("\n[Moon Dev] TOP MOST SKEWED ASSETS (squeeze candidates):")
for i, p in enumerate(position_data[:10]):
    if p['long_pct'] > 55:
        squeeze = "Crowded LONG -> shorts getting squeezed"
    else:
        squeeze = "Crowded SHORT -> potential SHORT SQUEEZE if price runs"
    print(f"  {i+1}. {p['symbol']:25s} L:{p['long_pct']:.1f}% S:{p['short_pct']:.1f}% skew:{p['skew']:.1f}% -> {squeeze}")

print("\n[Moon Dev] HEAVILY SHORTED ASSETS (short squeeze plays - oil momentum spillover):")
short_heavy = [p for p in position_data if p['short_pct'] > 55]
if short_heavy:
    for p in sorted(short_heavy, key=lambda x: x['short_pct'], reverse=True):
        print(f"  -> {p['symbol']:25s} {p['short_pct']:.1f}% short (${p['short_value']:,.0f})")
else:
    print("  None found with >55% short positioning")

print("\n[Moon Dev] HEAVILY LONGED ASSETS (long squeeze risk on reversal):")
long_heavy = [p for p in position_data if p['long_pct'] > 55]
if long_heavy:
    for p in sorted(long_heavy, key=lambda x: x['long_pct'], reverse=True):
        print(f"  -> {p['symbol']:25s} {p['long_pct']:.1f}% long (${p['long_value']:,.0f})")
else:
    print("  None found with >55% long positioning")

print("\n[Moon Dev] POSITIONED BUT QUIET - No 24h Liquidations (hidden moves brewing?):")
quiet_count = 0
for p in position_data:
    sym_short = p['symbol'].split(':')[-1] if ':' in p['symbol'] else p['symbol']
    has_liqs = any(sym_short.upper() in ls.upper() for ls in liq_symbols_set) or p['symbol'] in liq_symbols_set
    if not has_liqs and p['total_value'] > 500 and p['skew'] > 5:
        print(f"  -> {p['symbol']:25s} skew:{p['skew']:.1f}% {p['direction']}, ${p['total_value']:,.0f} exposure, NO recent liquidations")
        quiet_count += 1
if quiet_count == 0:
    print("  (All positioned assets had some liquidation activity)")

print("\n[Moon Dev] HIGHEST LIQUIDATION VOLUME 24H (most volatile / moving assets):")
if liq_by_symbol:
    top_liq = sorted(liq_by_symbol.items(), key=lambda x: x[1].get('total_value', 0) if isinstance(x[1], dict) else 0, reverse=True)
    for sym, d in top_liq[:10]:
        if isinstance(d, dict):
            tv = d.get('total_value', 0)
            lv = d.get('long_value', d.get('long_val', 0))
            sv = d.get('short_value', d.get('short_val', 0))
            bias = "short liqs > long liqs (price moving UP)" if sv > lv else "long liqs > short liqs (price moving DOWN)" if lv > sv else "balanced"
            print(f"  -> {sym:15s} ${tv:>12,.0f}  ({bias})")

print(f"\n{'='*80}")
print("  Moon Dev's TRADING INSIGHT:")
print("  - Oil (CL) ran up -> check COPPER, SILVER, GOLD for sympathy moves")
print("  - Heavily shorted assets are SHORT SQUEEZE candidates if momentum continues")
print("  - Assets with big positions but no liquidations = coiled spring")
print("  - Liq data showing short liqs = price going UP (shorts getting rekt)")
print("  - Liq data showing long liqs = price going DOWN (longs getting rekt)")
print(f"{'='*80}\n")
