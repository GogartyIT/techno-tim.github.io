import logging
import pandas as pd
import ccxt

import config
from models.trade import Trade, Side, Market

logger = logging.getLogger(__name__)


class BinanceClient:
    def __init__(self):
        self._exchange = ccxt.binance({
            "apiKey": config.BINANCE_API_KEY,
            "secret": config.BINANCE_SECRET_KEY,
        })
        # Point to Binance Testnet
        self._exchange.set_sandbox_mode(True)

    def get_bars(self, symbol: str, limit: int) -> pd.DataFrame:
        ohlcv = self._exchange.fetch_ohlcv(symbol, timeframe="1d", limit=limit)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return df

    def place_order(self, symbol: str, side: Side, qty: float) -> Trade:
        order_side = "buy" if side == Side.BUY else "sell"
        order = self._exchange.create_market_order(symbol, order_side, qty)
        logger.info("Binance order submitted: %s", order["id"])
        price = order.get("average") or order.get("price")
        return Trade(
            symbol=symbol,
            side=side,
            qty=qty,
            market=Market.BINANCE,
            price=float(price) if price else None,
            order_id=str(order["id"]),
        )

    def get_balance(self, currency: str = "USDT") -> float:
        try:
            balance = self._exchange.fetch_balance()
            return float(balance["free"].get(currency, 0.0))
        except Exception:
            return 0.0
