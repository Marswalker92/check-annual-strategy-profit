# Check Annual Strategy Profit

This project generates a daily cross-platform portfolio report for a fixed wallet list, can push the latest table to Telegram, keeps daily history, and generates a total floating PnL trend chart.

Sensitive data is not meant to live in tracked code files. The normal workflow is:

- keep your real secrets and wallet addresses in `config/local_config.json`
- keep only `config/local_config.example.json` in GitHub
- keep generated reports, histories, charts, and logs out of Git via `.gitignore`

## Layout

- `src/`: main source code
- `src/platforms/`: platform-specific API and balance logic
- `config/`: local secrets, wallet config, and safe examples
- `data/reports/`: generated markdown reports
- `data/history/`: generated JSON history files
- `data/charts/`: generated SVG charts
- `data/logs/`: cron runtime logs
- `README.md`: project usage and rule documentation

## Main Files

- `src/query_poly_positions.py`: main executable script, keeps argument parsing and orchestration
- `src/config_loader.py`: local config loading and secret resolution
- `src/wallets.py`: wallet record parsing and wallet source loading
- `src/platforms/polymarket.py`: Polymarket positions and Polygon `USDC.e` balance logic
- `src/platforms/opinion.py`: Opinion positions and BNB-chain `USDT` balance logic
- `src/reporting.py`: markdown and Telegram table rendering
- `src/history.py`: daily and monthly history read/write logic
- `src/charts.py`: SVG trend chart generation
- `src/telegram_push.py`: Telegram send helper
- `config/local_config.json`: real local-only config file, ignored by Git
- `config/local_config.example.json`: safe example config file to keep in GitHub
- `config/polymarket_wallets.example.txt`: optional wallet file format reference
- `data/reports/polymarket_portfolio_report.md`: latest generated daily report
- `data/history/polymarket_portfolio_history.json`: daily floating PnL snapshot history
- `data/history/total_floating_pnl_history.json`: daily history of the `总计` row's `当前浮动盈亏`
- `data/charts/total_floating_pnl_trend.svg`: SVG line chart generated from the daily total floating PnL history
- `data/reports/monthly-report.md`: latest generated monthly report
- `data/history/monthly_portfolio_history.json`: monthly portfolio snapshot history

## Local Config Format

The default runtime source is `config/local_config.json`.

Expected shape:

```json
{
  "telegram": {
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_TELEGRAM_CHAT_ID"
  },
  "opinion": {
    "api_key": "YOUR_OPINION_API_KEY"
  },
  "wallets": [
    {
      "name": "Example-Wallet",
      "owner_wallet": "0x1111111111111111111111111111111111111111",
      "poly_wallet": "0x2222222222222222222222222222222222222222",
      "op_wallet": "0x3333333333333333333333333333333333333333"
    }
  ]
}
```

## Wallet File Format

If you explicitly pass `--wallet-file`, these formats are supported:

- Legacy 2-column:
  `wallet_name, wallet_address`
- 3-column:
  `wallet_name, owner_wallet, poly_wallet`
- Preferred 4-column:
  `wallet_name, owner_wallet, poly_wallet, op_wallet`

Interpretation:

- `owner_wallet`: main wallet used to query Opinion positions
- `poly_wallet`: Polymarket wallet used to query Polymarket positions and Polygon USDC.e balance
- `op_wallet`: Opinion-side wallet used to query extra BNB-chain USDT balance

Special rule:

- If `op_wallet` is empty in the 4-column format, the extra Opinion-side USDT balance is treated as `0`
- It does not fall back to `owner_wallet`

## Report Contents

The generated report includes these columns:

- `钱包名称`
- `平台`
- `钱包地址`
- `portfolio`
- `初始成本`
- `当前浮动盈亏`
- `当天较前一天浮动盈亏变化`

Rows are rendered separately by platform:

- `Poly`
- `OP`

Rows whose visible numeric values round to `0.00` are hidden to keep the table compact.

The last column is:

`today floating_pnl - previous day floating_pnl`

The `总计` row in that last column is the sum of the day-over-day floating PnL changes across all rendered rows.

## Portfolio Calculation Rules

### Poly

`Poly portfolio` is:

- the Polymarket positions total from `poly_wallet`
- plus the Polygon `USDC.e` balance of `poly_wallet`

Current token used:

- `USDC.e`: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`

### OP

`OP portfolio` is:

- the Opinion positions total from `owner_wallet`
- plus the BNB-chain `USDT` balance of `op_wallet`

If `op_wallet` is empty, the extra USDT balance part is treated as `0`.

Current token used:

- `USDT`: `0x55d398326f99059fF775485246999027B3197955`

## History Logic

The script writes one floating PnL snapshot per rendered wallet row per UTC date into `data/history/polymarket_portfolio_history.json`.

When generating the current report, it looks up the previous UTC day in that history file and computes the new day-over-day column from that baseline.

If there is no snapshot for the previous day, the script falls back to `0.00` as the baseline for that wallet row.

In addition, the script records the `总计` row's `当前浮动盈亏` once per run into `data/history/total_floating_pnl_history.json`, then regenerates `data/charts/total_floating_pnl_trend.svg`.

The SVG chart is a 2D line chart:

- X axis: date
- Y axis: total current floating PnL

## Telegram Push

The script supports Telegram push with:

- values from `config/local_config.json`
- optional `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` environment variables
- optional CLI arguments:
  - `--send-telegram`
  - `--telegram-bot-token`
  - `--telegram-chat-id`

The Telegram message uses monospaced `<pre>` formatting and pads each column to improve alignment.

Sensitive Telegram credentials are intentionally not documented in this README.

## Manual Run

Generate only the local report:

```bash
cd /home/young-ai/code/polymarket_relate/check-annual-strategy-profit
python3 src/query_poly_positions.py
```

This default command reads:

- wallets from `config/local_config.json`
- Telegram credentials from `config/local_config.json` or env vars
- Opinion API key from `config/local_config.json` or env vars

Generate the report and send it to Telegram:

```bash
cd /home/young-ai/code/polymarket_relate/check-annual-strategy-profit
python3 src/query_poly_positions.py --send-telegram
```

Print the markdown table to stdout:

```bash
cd /home/young-ai/code/polymarket_relate/check-annual-strategy-profit
python3 src/query_poly_positions.py --stdout-table
```

Use an explicit wallet file only if needed:

```bash
cd /home/young-ai/code/polymarket_relate/check-annual-strategy-profit
python3 src/query_poly_positions.py --wallet-file config/polymarket_wallets.example.txt --stdout-table
```

Generate the monthly report:

```bash
cd /home/young-ai/code/polymarket_relate/check-annual-strategy-profit
python3 src/query_poly_positions.py --monthly-report
```

## Scheduled Run

A cron job is configured on this machine to run every day at `23:00`:

```cron
0 23 * * * cd /home/young-ai/code/polymarket_relate/check-annual-strategy-profit && /usr/bin/python3 src/query_poly_positions.py --send-telegram >> /home/young-ai/code/polymarket_relate/check-annual-strategy-profit/data/logs/report_cron.log 2>&1
```

This daily run also:

- updates `data/reports/polymarket_portfolio_report.md`
- updates `data/history/polymarket_portfolio_history.json`
- appends or refreshes the daily `总计` current floating PnL entry in `data/history/total_floating_pnl_history.json`
- regenerates `data/charts/total_floating_pnl_trend.svg`

A separate cron job is configured to run the monthly report at `22:00` on day `28` of each month:

```cron
0 22 28 * * * cd /home/young-ai/code/polymarket_relate/check-annual-strategy-profit && /usr/bin/python3 src/query_poly_positions.py --monthly-report --send-telegram >> /home/young-ai/code/polymarket_relate/check-annual-strategy-profit/data/logs/monthly_report_cron.log 2>&1
```

## Operational Notes

- The scheduled task runs only if the machine is powered on at the scheduled time
- After a reboot, cron remains configured and future daily runs continue automatically
- If the machine is offline exactly at the scheduled time, that missed run is not automatically replayed later
- Runtime logs are appended to `data/logs/`
- The daily SVG chart is generated locally; it does not materially increase API cost
