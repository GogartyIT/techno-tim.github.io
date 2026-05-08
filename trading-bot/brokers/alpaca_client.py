import logging
import pandas as pd
from datetime import datetime, timedelta, timezone

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

import config
from models.trade import Trade, Side, Market

logger = logging.getLogger(__name__)


class AlpacaClient:
    def __init__(self):
        self._trading = TradingClient(
            config.ALPACA_API_KEY,
            config.ALPACA_SECRET_KEY,
            paper=True,
        )
        self._data = StockHistoricalDataClient(
            config.ALPACA_API_KEY,
            config.ALPACA_SECRET_KEY,
        )

    def get_bars(self, symbol: str, limit: int) -> pd.DataFrame:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=limit * 2)  # buffer for weekends/holidays
        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            limit=limit,
        )
        bars = self._data.get_stock_bars(req)
        df = bars.df
        if isinstance(df.index, pd.MultiIndex):
            df = df.xs(symbol, level="symbol")
        return df.reset_index()

    def place_order(self, symbol: str, side: Side, qty: float) -> Trade:
        order_side = OrderSide.BUY if side == Side.BUY else OrderSide.SELL
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY,
        )
        order = self._trading.submit_order(req)
        logger.info("Alpaca order submitted: %s", order.id)
        return Trade(
            symbol=symbol,
            side=side,
            qty=qty,
            market=Market.ALPACA,
            order_id=str(order.id),
        )

    def get_position(self, symbol: str) -> float:
        try:
            pos = self._trading.get_open_position(symbol)
            return float(pos.qty)
        except Exception:
            return 0.0
