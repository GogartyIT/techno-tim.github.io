"""
Moving Average Crossover strategy.

Signal logic:
  - BUY  when the fast MA crosses *above* the slow MA (golden cross)
  - SELL when the fast MA crosses *below* the slow MA (death cross)
  - HOLD otherwise
"""
import pandas as pd
from enum import Enum


class Signal(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


def compute_signal(df: pd.DataFrame, fast: int, slow: int) -> Signal:
    """Return a Signal given a DataFrame with a 'close' column."""
    if len(df) < slow + 1:
        return Signal.HOLD

    closes = df["close"].astype(float)
    fast_ma = closes.rolling(fast).mean()
    slow_ma = closes.rolling(slow).mean()

    prev_fast, curr_fast = fast_ma.iloc[-2], fast_ma.iloc[-1]
    prev_slow, curr_slow = slow_ma.iloc[-2], slow_ma.iloc[-1]

    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return Signal.BUY
    if prev_fast >= prev_slow and curr_fast < curr_slow:
        return Signal.SELL
    return Signal.HOLD
