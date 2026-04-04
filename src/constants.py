from __future__ import annotations

import re
from pathlib import Path

API_BASE = "https://data-api.polymarket.com/positions"
OPINION_API_BASE = "https://openapi.opinion.trade/openapi/positions/user"
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
BSC_RPC_URL = "https://bsc-dataseed.binance.org/"
POLYGON_RPC_URL = "https://polygon-bor-rpc.publicnode.com"
USDT_TOKEN_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"
POLY_USDCE_TOKEN_CONTRACT = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_DIR / "config"
DATA_DIR = PROJECT_DIR / "data"
REPORTS_DIR = DATA_DIR / "reports"
HISTORY_DIR = DATA_DIR / "history"
CHARTS_DIR = DATA_DIR / "charts"

DEFAULT_WALLET_FILE = CONFIG_DIR / "polymarket_wallets.example.txt"
DEFAULT_OUTPUT_FILE = REPORTS_DIR / "polymarket_portfolio_report.md"
DEFAULT_HISTORY_FILE = HISTORY_DIR / "polymarket_portfolio_history.json"
DEFAULT_TOTAL_FLOATING_PNL_HISTORY_FILE = (
    HISTORY_DIR / "total_floating_pnl_history.json"
)
DEFAULT_TOTAL_FLOATING_PNL_CHART_FILE = CHARTS_DIR / "total_floating_pnl_trend.png"
DEFAULT_MONTHLY_OUTPUT_FILE = REPORTS_DIR / "monthly-report.md"
DEFAULT_MONTHLY_HISTORY_FILE = HISTORY_DIR / "monthly_portfolio_history.json"
DEFAULT_CONFIG_FILE = CONFIG_DIR / "local_config.json"

DEFAULT_UNSETTLED_MARKETS_FILE = REPORTS_DIR / "unsettled_markets.md"
DEFAULT_UNSETTLED_MARKETS_JSON = REPORTS_DIR / "unsettled_markets.json"
DEFAULT_UNSETTLED_BY_MARKET_FILE = REPORTS_DIR / "unsettled_by_market.md"
DEFAULT_UNSETTLED_BY_MARKET_JSON = REPORTS_DIR / "unsettled_by_market.json"

ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
