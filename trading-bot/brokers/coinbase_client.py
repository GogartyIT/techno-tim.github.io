import logging
import pandas as pd
import ccxt

import config
from models.trade import Trade, Side, Market

logger = logging.getLogger(__name__)


class CoinbaseClient:
    def __init__(self):
        # coinbaseadvancedtrade uses JWT-based API keys from https://portal.cdp.coinbase.com/
        self._exchange = ccxt.coinbaseadvancedtrade({
            "apiKey": config.COINBASE_API_KEY,
            "secret": config.COINBASE_SECRET_KEY,
        })
        # Coinbase Advanced Trade sandbox
        self._exchange.set_sandbox_mode(True)

    def get_bars(self, symbol: str, limit: int) -> pd.DataFrame:
        # Coinbase uses "BTC-USD" format; ccxt normalises it as "BTC/USD"
        ccxt_symbol = symbol.replace("-", "/")
        ohlcv = self._exchange.fetch_ohlcv(ccxt_symbol, timeframe="1d", limit=limit)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return df

    def place_order(self, symbol: str, side: Side, qty: float) -> Trade:
        ccxt_symbol = symbol.replace("-", "/")
        order_side = "buy" if side == Side.BUY else "sell"
        order = self._exchange.create_market_order(ccxt_symbol, order_side, qty)
        logger.info("Coinbase order submitted: %s", order["id"])
        price = order.get("average") or order.get("price")
        return Trade(
            symbol=symbol,
            side=side,
            qty=qty,
            market=Market.COINBASE,
            price=float(price) if price else None,
            order_id=str(order["id"]),
        )

    def get_balance(self, currency: str = "USD") -> float:
        try:
            balance = self._exchange.fetch_balance()
            return float(balance["free"].get(currency, 0.0))
        except Exception:
            return 0.0
