# Polymarket Profitable Traders

> 🌙 Moon Dev's Polymarket Profitable Traders endpoint — follow the smart money in prediction markets.

Find the most profitable traders on Polymarket, ranked by 7-day P&L. Moon Dev's
backend continuously scans Polymarket and surfaces the wallets actually making
money, so you can follow the smart money in prediction markets.

---

## Overview

| | |
|---|---|
| **Endpoint** | `GET /api/poly/profitable-traders` |
| **SDK method** | `MoonDevAPI().get_poly_profitable_traders()` |
| **Example** | `examples/34_polymarket_traders.py` |
| **Auth** | API key required (`MOONDEV_API_KEY`) |
| **Parameters** | None |

---

## How traders are discovered

The service finds profitable traders from two live discovery sources, then keeps
only the wallets clearing a **$300+ 7-day P&L** threshold:

- **BTC 5m** (`source: "btc_5m"`) — traders active in BTC 5-minute prediction markets.
- **Trending** (`source: "trending"`) — traders making big trades ($500+) in trending markets.

Results are always sorted by **7-day P&L, highest first**.

---

## Access tiers

| Tier | API key | What you get |
|------|---------|--------------|
| **Standard** | regular key | Top 25 traders |
| **Quant Elite** | `_qe` key | Full list of all profitable traders |

The `full_list` field in the response confirms which tier you received
(`true` = full Quant Elite list, `false` = standard top 25).

---

## Request

No parameters needed — just call the endpoint with your API key.

```python
from api import MoonDevAPI

api = MoonDevAPI()
data = api.get_poly_profitable_traders()

for t in data["traders"]:
    print(t["wallet"], t["pnl_7d"], t["source"])
```

---

## Response

```jsonc
{
  "total": 25,                       // number of traders returned
  "full_list": false,                // true = QE full list, false = standard top 25
  "updated_at": "2026-06-05T12:00:00Z", // ISO 8601 timestamp of last refresh
  "stats": {
    "wallets_checked": 12345,        // total wallets scanned by the service
    "queue_depth": 8,                // wallets pending a scan
    "uptime_minutes": 240            // service uptime
  },
  "traders": [                       // sorted by pnl_7d DESC
    {
      "wallet": "0xabc...def",
      "polymarket_link": "https://polymarket.com/0xabc...def",
      "pnl_7d": 1234.56,             // 7-day profit & loss (USD)
      "volume_7d": 45678.90,         // 7-day trading volume (USD)
      "trades_7d": 42,               // number of trades in last 7 days
      "redeems_7d": 30,              // winning redemptions ("wins")
      "discovered_at": "2026-06-04T09:30:00Z",
      "source": "btc_5m"            // discovery source: "btc_5m" or "trending"
    }
  ]
}
```

### Field reference

**Top level**

| Field | Type | Description |
|-------|------|-------------|
| `total` | int | Number of traders in the response. |
| `full_list` | bool | `true` for Quant Elite full list, `false` for standard top 25. |
| `updated_at` | string | ISO 8601 timestamp of the last data refresh. |
| `stats` | object | Service health metrics (see below). |
| `traders` | array | List of trader objects, sorted by `pnl_7d` descending. |

**`stats` object**

| Field | Type | Description |
|-------|------|-------------|
| `wallets_checked` | int | Total wallets scanned by the service. |
| `queue_depth` | int | Wallets currently pending a scan. |
| `uptime_minutes` | float | Service uptime in minutes. |

**Each `traders` object**

| Field | Type | Description |
|-------|------|-------------|
| `wallet` | string | Trader's wallet address — **use this as the unique identifier**. |
| `polymarket_link` | string | Wallet-based Polymarket profile URL (`https://polymarket.com/<wallet>`). |
| `pnl_7d` | float | 7-day profit & loss in USD. |
| `volume_7d` | float | 7-day trading volume in USD. |
| `trades_7d` | int | Number of trades in the last 7 days. |
| `redeems_7d` | int | Winning redemptions (displayed as "wins"). |
| `discovered_at` | string | ISO 8601 timestamp the trader was first discovered. |
| `source` | string | Discovery source: `"btc_5m"` or `"trending"`. |

> **Note:** As of 2026-04-14, the `name` and `display_name` fields were removed
> (Polymarket pseudonyms proved unreliable). Use `wallet` as the trader
> identifier, and `polymarket_link` for the profile URL.

---

## Run the example

```bash
python examples/34_polymarket_traders.py
```

The example renders a full terminal dashboard: a service-stats panel, a detailed
**Top 10** leaderboard, a compact full list, summary stat cards (combined P&L,
combined volume, total trades, and a discovery-source breakdown), and a footer.

---

## Related Polymarket endpoints

- `GET /api/poly/whales` — live whale trade log ($1,000+ fills, newest first)
- `GET /api/poly/whales/top-traders` — whale leaderboard by wallet
- `GET /api/poly/whales/top-markets` — whale leaderboard by market
- `GET /api/poly/whales/daily` — per-day whale activity rollup (charting)
- `GET /api/poly/whales/health` — whale ingestion status (no auth)
- `GET /api/poly/health` — Polymarket service health (no auth)

---

🌙 *Built with love by Moon Dev — moondev.com/docs*
