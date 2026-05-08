from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class Market(str, Enum):
    ALPACA = "alpaca"
    BINANCE = "binance"
    COINBASE = "coinbase"


@dataclass
class Trade:
    symbol: str
    side: Side
    qty: float
    market: Market
    price: float | None = None
    order_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __str__(self) -> str:
        price_str = f" @ ${self.price:.4f}" if self.price else ""
        return f"[{self.market.value.upper()}] {self.side.value.upper()} {self.qty} {self.symbol}{price_str}"
