import os
from dotenv import load_dotenv

load_dotenv()

# --- Alpaca (paper trading) ---
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")

# --- Binance (testnet) ---
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")

# --- Coinbase Advanced Trade (sandbox) ---
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY", "")
COINBASE_SECRET_KEY = os.getenv("COINBASE_SECRET_KEY", "")

# --- Assets to trade ---
STOCK_SYMBOLS = ["AAPL", "TSLA", "MSFT"]
BINANCE_SYMBOLS = ["BTC/USDT", "ETH/USDT"]
COINBASE_SYMBOLS = ["BTC-USD", "ETH-USD"]

# --- Strategy parameters ---
FAST_MA = 10   # bars
SLOW_MA = 20   # bars
BAR_LIMIT = 50  # how many historical bars to fetch

# Order sizes (paper/testnet — small intentionally)
STOCK_QTY = 1        # shares
CRYPTO_QTY = 0.001   # BTC-sized units

# --- Scheduler ---
RUN_INTERVAL_MINUTES = 1440   # once per day
