# Check Annual Strategy Profit

This project generates portfolio reports for a fixed wallet list across `Polymarket` and `Opinion`.

It supports:

- daily report generation
- monthly summary generation
- Telegram push
- Telegram `/check` command for on-demand report generation
- daily total floating PnL history and chart output

Sensitive data is intentionally kept out of tracked code. Real secrets and wallet addresses should stay in a local-only config file.

## Repository Layout

- `src/`: source code
- `src/platforms/`: platform-specific fetch and balance logic
- `config/`: config examples
- `data/`: generated reports, history, charts, and logs

## Local Config

Runtime expects a local config file with this shape:

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

Tracked files only include examples such as:

- `config/local_config.example.json`
- `config/polymarket_wallets.example.txt`
- `config/op_test_wallets.example.txt`

## Wallet Model

Supported wallet formats when using a wallet file:

- `wallet_name, wallet_address`
- `wallet_name, owner_wallet, poly_wallet`
- `wallet_name, owner_wallet, poly_wallet, op_wallet`

Meaning:

- `owner_wallet`: used for `Opinion` positions
- `poly_wallet`: used for `Polymarket` positions and Polygon `USDC.e` balance
- `op_wallet`: used for extra BNB-chain `USDT` balance on the `Opinion` side

If `op_wallet` is empty, the extra `USDT` balance is treated as `0`.

## Report Rules

Report columns:

- `钱包名称`
- `平台`
- `钱包地址`
- `portfolio`
- `初始成本`
- `当前浮动盈亏`
- `当天较前一天浮动盈亏变化`

Rendering rules:

- `Poly` and `OP` are shown as separate rows
- rows that round to all-zero visible values are hidden
- the final column is day-over-day floating PnL change
- the `总计` row sums rendered rows only

## Portfolio Logic

`Poly portfolio`:

- Polymarket positions total from `poly_wallet`
- plus Polygon `USDC.e` balance of `poly_wallet`

`OP portfolio`:

- Opinion positions total from `owner_wallet`
- plus BNB-chain `USDT` balance of `op_wallet`

## Outputs

Typical generated files:

- daily markdown report
- monthly markdown report
- daily wallet floating PnL history
- monthly portfolio history
- daily total floating PnL history
- daily total floating PnL PNG chart

Output directory convention:

- markdown reports are saved in `data/reports/`
- generated JSON files are saved in `data/reports/json/`
- charts are saved in `data/charts/`

## Usage

Examples:

```bash
python3 src/query_poly_positions.py
python3 src/query_poly_positions.py --send-telegram
python3 src/query_poly_positions.py --monthly-report
python3 src/query_poly_positions.py --stdout-table
python3 src/telegram_command_bot.py
```

Telegram command bot behavior:

- `/check`: run the latest report immediately and send the current table
- `/start`
- `/help`

## Automation

Typical deployment keeps two automation paths:

- a scheduled daily report run
- a long-running Telegram command listener for `/check`

Exact machine-specific service definitions, local paths, and scheduler commands are intentionally not documented here.

## Git Safety

Do not commit:

- real local config files
- generated data files
- logs
- cache files

Use `.gitignore` to keep local secrets and runtime artifacts out of GitHub.
