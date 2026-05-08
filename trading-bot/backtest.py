#!/usr/bin/env python3
"""
Backtest: $50 starting capital, MA crossover strategy.
Period:   May 1–8 2026  (daily bars — one signal check per day)
Data:     Synthetic price paths using Geometric Brownian Motion
          seeded from realistic May 2026 price estimates.

NOTE: Real network access is unavailable in this environment.
      Prices are synthetic but use realistic volatility parameters.
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

# ── Simulation config ─────────────────────────────────────────────────────────
START   = datetime(2026, 5, 1, tzinfo=timezone.utc)
END     = datetime(2026, 5, 8, tzinfo=timezone.utc)
CAPITAL = 50.0
FAST_MA = 10
SLOW_MA = 20
WARMUP  = 60   # calendar days of warmup so MA is established by May 1

RNG_SEED = 42  # fixed seed → reproducible results

# Realistic starting prices (estimates for early May 2026)
# and DAILY volatility (annualised vol / sqrt(252 trading days))
ASSETS = {
    #  symbol         start_price   daily_vol   annual_drift
    "AAPL":           (212.40,      0.0158,      0.12),
    "TSLA":           (318.75,      0.0378,      0.18),
    "MSFT":           (468.20,      0.0139,      0.11),
    "BTC/USDT":       (96_800.00,   0.0504,      0.40),
    "ETH/USDT":       (3_480.00,    0.0567,      0.35),
}

ALL_SYMBOLS = list(ASSETS.keys())
ALLOC = CAPITAL / len(ALL_SYMBOLS)

# ── Synthetic price generation ────────────────────────────────────────────────

STOCK_SYMBOLS  = {"AAPL", "TSLA", "MSFT"}
WEEKEND_DAYS   = {5, 6}   # Saturday=5, Sunday=6


def generate_bars(symbol: str, rng: np.random.Generator) -> pd.DataFrame:
    s0, sigma, drift_annual = ASSETS[symbol]
    mu_daily = drift_annual / 252
    is_stock = symbol in STOCK_SYMBOLS

    # Walk from warmup start to END, keeping valid trading days
    warmup_start = START - timedelta(days=WARMUP * 2)   # 2x buffer absorbs weekends
    days, d = [], warmup_start
    while d <= END:
        if not is_stock or d.weekday() not in WEEKEND_DAYS:
            days.append(d)
        d += timedelta(days=1)

    returns = rng.normal(mu_daily, sigma, len(days))
    prices  = s0 * np.exp(np.cumsum(returns) - returns[0])
    return pd.DataFrame({"timestamp": days, "close": prices})


# ── Strategy signals ──────────────────────────────────────────────────────────

def add_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["fast_ma"] = df["close"].rolling(FAST_MA).mean()
    df["slow_ma"] = df["close"].rolling(SLOW_MA).mean()

    prev_fast = df["fast_ma"].shift(1)
    prev_slow = df["slow_ma"].shift(1)

    df["signal"] = "hold"
    df.loc[(prev_fast <= prev_slow) & (df["fast_ma"] > df["slow_ma"]), "signal"] = "buy"
    df.loc[(prev_fast >= prev_slow) & (df["fast_ma"] < df["slow_ma"]), "signal"] = "sell"
    return df


# ── Per-asset backtest ────────────────────────────────────────────────────────

def backtest_asset(symbol: str, df_full: pd.DataFrame, starting_cash: float) -> dict:
    df  = add_signals(df_full)
    sim = df[(df["timestamp"] >= START) & (df["timestamp"] <= END)].copy().reset_index(drop=True)

    cash        = starting_cash
    units       = 0.0
    entry_price = None
    trades      = []

    for _, row in sim.iterrows():
        price  = row["close"]
        sig    = row["signal"]
        ts_str = row["timestamp"].strftime("%b %d")

        if sig == "buy" and cash > 0:
            units       = cash / price
            entry_price = price
            trades.append(dict(time=ts_str, action="BUY",
                               price=price, units=units, value=cash))
            cash = 0.0

        elif sig == "sell" and units > 0:
            value = units * price
            pnl   = value - units * entry_price
            trades.append(dict(time=ts_str, action="SELL",
                               price=price, units=units, value=value, pnl=pnl))
            cash        = value
            units       = 0.0
            entry_price = None

    last_price  = sim["close"].iloc[-1]
    final_value = cash + units * last_price

    return dict(
        symbol=symbol,
        start_price=ASSETS[symbol][0],
        end_price=last_price,
        price_chg_pct=(last_price - ASSETS[symbol][0]) / ASSETS[symbol][0] * 100,
        start_cash=starting_cash,
        final_value=final_value,
        pnl=final_value - starting_cash,
        pnl_pct=(final_value - starting_cash) / starting_cash * 100,
        trades=trades,
        open_units=units,
        last_price=last_price,
    )


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(results: list) -> None:
    total_start = sum(r["start_cash"]  for r in results)
    total_end   = sum(r["final_value"] for r in results)
    total_pnl   = total_end - total_start
    pnl_pct     = total_pnl / total_start * 100

    print()
    print("╔" + "═"*60 + "╗")
    print("║  SIMULATED BACKTEST  ·  May 1–8 2026  ·  MA 10/20 Daily bars ║"[:62])
    print("║  ⚠  Synthetic price data (GBM) — for illustration only       ║"[:62])
    print("╠" + "═"*60 + "╣")
    print(f"║  Starting capital: ${CAPITAL:.2f}  ·  Equal-weight across {len(results)} assets"[:62] + " ║"[:max(0, 63 - len(f"║  Starting capital: ${CAPITAL:.2f}  ·  Equal-weight across {len(results)} assets"))])

    for r in results:
        print("╠" + "─"*60 + "╣")
        arrow  = "▲" if r["pnl"] >= 0 else "▼"
        p_arrow = "▲" if r["price_chg_pct"] >= 0 else "▼"
        print(f"║  {r['symbol']:<10}"
              f"  price {p_arrow}{abs(r['price_chg_pct']):.1f}%"
              f"  |  ${r['start_cash']:.2f} → ${r['final_value']:.2f}"
              f"  {arrow}{abs(r['pnl']):.2f} ({r['pnl_pct']:+.1f}%)")

        if r["trades"]:
            for t in r["trades"]:
                tag     = "  ▶ BUY " if t["action"] == "BUY" else "  ◀ SELL"
                pnl_str = f"  gain/loss: {t['pnl']:+.4f}" if "pnl" in t else ""
                print(f"║     {tag} {t['time']}  @ ${t['price']:>12,.2f}{pnl_str}")
        else:
            print("║     — no crossover signals during this period —")

        if r["open_units"] > 0:
            mkt = r["open_units"] * r["last_price"]
            print(f"║     [open position: {r['open_units']:.6f} units"
                  f" @ ${r['last_price']:,.2f} = ${mkt:.2f}]")

    print("╠" + "═"*60 + "╣")
    arrow = "▲" if total_pnl >= 0 else "▼"
    print(f"║  TOTAL   ${total_start:.2f} → ${total_end:.2f}"
          f"   {arrow} ${abs(total_pnl):.2f}  ({pnl_pct:+.1f}%)")
    print("╚" + "═"*60 + "╝")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    rng     = np.random.default_rng(RNG_SEED)
    results = []

    print(f"\nRunning backtest: ${CAPITAL:.0f} across {len(ALL_SYMBOLS)} assets"
          f"  |  {ALLOC:.2f}/asset  |  MA {FAST_MA}/{SLOW_MA}")

    for sym in ALL_SYMBOLS:
        df = generate_bars(sym, rng)
        r  = backtest_asset(sym, df, ALLOC)
        results.append(r)

    print_report(results)


if __name__ == "__main__":
    main()
