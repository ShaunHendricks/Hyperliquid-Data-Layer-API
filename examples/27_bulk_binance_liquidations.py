"""
🌙 Moon Dev's Bulk Binance Liquidation Data Downloader
Built with love by Moon Dev 🚀

Downloads 18+ months of Binance Futures liquidation data (32M+ records back to June 2024)
Requires a Quant Elite API key (must end in _qe)

Endpoint: GET /api/bulk/binance_liquidations?api_key=YOUR_QE_KEY
Response is paginated (10,000 records per page) - this script auto-paginates through all data.

Supports filters: start, end, symbol, side, min_usd
"""

import sys
import os
import requests
import pandas as pd
from datetime import datetime

# Add parent directory to path for importing api.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

# ==================== CONFIG ====================
BASE_URL = "https://api.moondev.com"
ENDPOINT = "/api/bulk/binance_liquidations"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Optional filters - set to None to skip
SYMBOL = None          # e.g. "BTC", "ETH", None for all
SIDE = None            # "BUY" or "SELL", None for all
MIN_USD = None         # minimum usd_size filter, e.g. 1000
START_DATE = None      # e.g. "2024-06-01"
END_DATE = None        # e.g. "2025-01-01"


def main():
    """🌙 Moon Dev's Bulk Binance Liquidation Downloader"""
    print("🌙 Moon Dev's Bulk Binance Liquidation Downloader")
    print("=" * 60)

    api_key = os.getenv('MOONDEV_API_KEY')
    if not api_key:
        print("❌ Moon Dev says: No API key found! Set MOONDEV_API_KEY in your .env file")
        return

    if not api_key.endswith('_qe'):
        print("⚠️  Moon Dev Warning: This endpoint requires a Quant Elite key (ending in _qe)")
        print(f"   Your key ends with: ...{api_key[-4:]}")
        print("   Attempting anyway...\n")

    print(f"🔑 Moon Dev: API key loaded (...{api_key[-4:]})")
    print(f"📡 Moon Dev: Fetching bulk liquidation data (paginated, 10k per page)")

    # Build params
    params = {"api_key": api_key}
    if SYMBOL:
        params["symbol"] = SYMBOL
    if SIDE:
        params["side"] = SIDE
    if MIN_USD:
        params["min_usd"] = MIN_USD
    if START_DATE:
        params["start"] = START_DATE
    if END_DATE:
        params["end"] = END_DATE

    if any([SYMBOL, SIDE, MIN_USD, START_DATE, END_DATE]):
        print(f"🔍 Moon Dev: Filters applied: {params}")

    # Paginate through all data
    all_records = []
    offset = 0
    total_records = None

    while True:
        params["offset"] = offset
        url = f"{BASE_URL}{ENDPOINT}"

        response = requests.get(url, params=params, timeout=120)
        response.raise_for_status()
        result = response.json()

        if total_records is None:
            total_records = result.get("total_records", 0)
            print(f"📊 Moon Dev: Total records available: {total_records:,}")

        batch = result.get("data", [])
        if not batch:
            break

        all_records.extend(batch)
        returned = result.get("returned", len(batch))
        has_more = result.get("has_more", False)

        print(f"   📥 Page {offset // 10000 + 1}: fetched {returned:,} records | total downloaded: {len(all_records):,} / {total_records:,}")

        if not has_more:
            break

        offset = result.get("next_offset", offset + 10000)

    print(f"\n✅ Moon Dev: All pages downloaded! Total records: {len(all_records):,}")

    # Convert to DataFrame
    df = pd.DataFrame(all_records)
    print(f"📊 Moon Dev: DataFrame shape: {df.shape}")
    print(f"   Columns: {list(df.columns)}")

    # Save to CSV
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = os.path.join(OUTPUT_DIR, f"bulk_binance_liquidations_{timestamp}.csv")
    df.to_csv(csv_file, index=False)

    size_mb = os.path.getsize(csv_file) / (1024 * 1024)
    print(f"\n💾 Moon Dev: Saved to {csv_file}")
    print(f"   📏 Size: {size_mb:.1f} MB")
    print(f"   📏 Rows: {len(df):,}")

    # Preview
    print(f"\n🔥 Moon Dev: First 10 rows:")
    print(df.head(10).to_string(index=False))

    # Quick stats
    if 'usd_size' in df.columns:
        print(f"\n📈 Moon Dev: Quick Stats:")
        print(f"   Total USD volume: ${df['usd_size'].sum():,.2f}")
        if 'side' in df.columns:
            for side in df['side'].unique():
                side_df = df[df['side'] == side]
                print(f"   {side}: {len(side_df):,} records, ${side_df['usd_size'].sum():,.2f}")
        if 'symbol' in df.columns:
            top_symbols = df.groupby('symbol')['usd_size'].sum().sort_values(ascending=False).head(10)
            print(f"\n   Top 10 symbols by USD volume:")
            for sym, vol in top_symbols.items():
                print(f"     {sym}: ${vol:,.2f}")

    print(f"\n🌙 Moon Dev: Bulk liquidation download complete! 🚀")


if __name__ == "__main__":
    main()
