#!/usr/bin/env python3
"""
Backtest comparison — May 1–8 2026, daily bars, $40 DCA vs $50 MA strategy vs $40 Buy & Hold.
Data: Synthetic GBM with realistic May 2026 price estimates (no network required).
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

# ── Config ────────────────────────────────────────────────────────────────────
START    = datetime(2026, 5, 1, tzinfo=timezone.utc)
END      = datetime(2026, 5, 8, tzinfo=timezone.utc)
WARMUP   = 60    # calendar days before START for MA warm-up
RNG_SEED = 42

MA_CAPITAL  = 50.0   # MA strategy capital
DCA_CAPITAL = 40.0   # DCA / buy-and-hold capital
FAST_MA     = 10
SLOW_MA     = 20

ASSETS = {
    #  symbol         start_price   daily_vol   annual_drift
    "AAPL":           (212.40,      0.0158,      0.12),
    "TSLA":           (318.75,      0.0378,      0.18),
    "MSFT":           (468.20,      0.0139,      0.11),
    "BTC/USDT":       (96_800.00,   0.0504,      0.40),
    "ETH/USDT":       (3_480.00,    0.0567,      0.35),
}

ALL_SYMBOLS  = list(ASSETS.keys())
STOCK_SYMS   = {"AAPL", "TSLA", "MSFT"}
WEEKEND_DAYS = {5, 6}

# ── Price generation ──────────────────────────────────────────────────────────

def generate_bars(symbol: str, rng: np.random.Generator) -> pd.DataFrame:
    s0, sigma, drift_annual = ASSETS[symbol]
    mu_daily  = drift_annual / 252
    is_stock  = symbol in STOCK_SYMS
    warmup_start = START - timedelta(days=WARMUP * 2)
    days, d = [], warmup_start
    while d <= END:
        if not is_stock or d.weekday() not in WEEKEND_DAYS:
            days.append(d)
        d += timedelta(days=1)
    returns = rng.normal(mu_daily, sigma, len(days))
    prices  = s0 * np.exp(np.cumsum(returns) - returns[0])
    return pd.DataFrame({"timestamp": days, "close": prices})


def sim_window(df: pd.DataFrame) -> pd.DataFrame:
    mask = (df["timestamp"] >= START) & (df["timestamp"] <= END)
    return df[mask].copy().reset_index(drop=True)

# ── Strategy 1: MA Crossover ──────────────────────────────────────────────────

def run_ma(symbol: str, df_full: pd.DataFrame, alloc: float) -> dict:
    df = df_full.copy()
    df["fast_ma"] = df["close"].rolling(FAST_MA).mean()
    df["slow_ma"] = df["close"].rolling(SLOW_MA).mean()
    pf = df["fast_ma"].shift(1); ps = df["slow_ma"].shift(1)
    df["signal"] = "hold"
    df.loc[(pf <= ps) & (df["fast_ma"] > df["slow_ma"]), "signal"] = "buy"
    df.loc[(pf >= ps) & (df["fast_ma"] < df["slow_ma"]), "signal"] = "sell"

    sim   = sim_window(df)
    cash  = alloc
    units = 0.0
    entry = None
    trades = []

    for _, row in sim.iterrows():
        price = row["close"]; sig = row["signal"]
        ts    = row["timestamp"].strftime("%b %d")
        if sig == "buy" and cash > 0:
            units = cash / price; entry = price
            trades.append(dict(day=ts, action="BUY", price=price, spent=cash))
            cash = 0.0
        elif sig == "sell" and units > 0:
            value = units * price
            trades.append(dict(day=ts, action="SELL", price=price,
                               value=value, pnl=value - units * entry))
            cash = value; units = 0.0; entry = None

    last  = sim["close"].iloc[-1]
    final = cash + units * last
    return dict(symbol=symbol, alloc=alloc, final=final,
                pnl=final - alloc, trades=trades,
                start_price=ASSETS[symbol][0], end_price=last)

# ── Strategy 2: Dollar-Cost Averaging ────────────────────────────────────────

def run_dca(symbol: str, df_full: pd.DataFrame, alloc: float) -> dict:
    """Buy a fixed dollar amount each trading day, never sell."""
    sim        = sim_window(df_full)
    n_days     = len(sim)
    daily_spend = alloc / n_days   # equal slice per bar
    units      = 0.0
    buys       = []

    for _, row in sim.iterrows():
        price  = row["close"]
        bought = daily_spend / price
        units += bought
        buys.append(dict(
            day=row["timestamp"].strftime("%b %d"),
            price=price,
            spent=daily_spend,
            units=bought,
        ))

    last  = sim["close"].iloc[-1]
    final = units * last
    avg_cost = alloc / units if units else 0

    return dict(symbol=symbol, alloc=alloc, final=final,
                pnl=final - alloc, buys=buys, units=units,
                avg_cost=avg_cost,
                start_price=ASSETS[symbol][0], end_price=last)

# ── Strategy 3: Buy & Hold ────────────────────────────────────────────────────

def run_hold(symbol: str, df_full: pd.DataFrame, alloc: float) -> dict:
    """Buy everything on day 1, hold to end."""
    sim        = sim_window(df_full)
    buy_price  = sim["close"].iloc[0]
    units      = alloc / buy_price
    last       = sim["close"].iloc[-1]
    final      = units * last
    return dict(symbol=symbol, alloc=alloc, final=final,
                pnl=final - alloc, buy_price=buy_price,
                start_price=ASSETS[symbol][0], end_price=last)

# ── Report ────────────────────────────────────────────────────────────────────

W = 80

def _pct(val: float, base: float) -> str:
    p = val / base * 100
    return f"{p:+.1f}%"

def _arrow(val: float) -> str:
    return "▲" if val >= 0 else "▼"


def print_report(ma_results, dca_results, hold_results) -> None:
    ma_total   = sum(r["final"] for r in ma_results)
    dca_total  = sum(r["final"] for r in dca_results)
    hold_total = sum(r["final"] for r in hold_results)

    bar = "═" * (W - 2)
    thin = "─" * (W - 2)

    def row(text: str) -> str:
        return f"║  {text:<{W-4}}║"

    print()
    print("╔" + bar + "╗")
    print(row("BACKTEST  ·  May 1–8 2026  ·  Daily Bars  ·  Synthetic GBM data"))
    print(row(f"{'Asset':<12}  {'MA 10/20  ($50 total)':^22}  {'DCA  ($40 total)':^20}  {'Buy&Hold  ($40 total)':^20}"))
    print("╠" + thin + "╣")

    for ma, dca, hold in zip(ma_results, dca_results, hold_results):
        price_chg = (ma["end_price"] - ma["start_price"]) / ma["start_price"] * 100
        ma_s   = f"${ma['final']:6.2f}  ({_pct(ma['pnl'],   ma['alloc'])})"
        dca_s  = f"${dca['final']:6.2f}  ({_pct(dca['pnl'],  dca['alloc'])})"
        hold_s = f"${hold['final']:6.2f}  ({_pct(hold['pnl'], hold['alloc'])})"
        p_tag  = f"price {_arrow(price_chg)}{abs(price_chg):.1f}%"
        print(row(f"{ma['symbol']:<12} {ma_s:<24} {dca_s:<22} {hold_s}"))
        print(row(f"  {p_tag:<18} DCA avg ${dca['avg_cost']:,.2f}  →  end ${dca['end_price']:,.2f}"))

        if ma["trades"]:
            for t in ma["trades"]:
                tag = "▶ BUY" if t["action"] == "BUY" else "◀ SELL"
                pnl = f"  P&L {t['pnl']:+.3f}" if "pnl" in t else ""
                print(row(f"  MA {tag} {t['day']} @ ${t['price']:>12,.2f}{pnl}"))
        else:
            print(row("  MA — no crossover signal this week (cash held)"))
        print("╠" + thin + "╣")

    # ── Summary ────────────────────────────────────────────────────────────────
    ma_pnl   = ma_total  - MA_CAPITAL
    dca_pnl  = dca_total - DCA_CAPITAL
    hold_pnl = hold_total - DCA_CAPITAL

    print(row(f"{'TOTALS':<12}  ${ma_total:6.2f}  ({_pct(ma_pnl, MA_CAPITAL):<8})  ${dca_total:6.2f}  ({_pct(dca_pnl, DCA_CAPITAL):<8})  ${hold_total:6.2f}  ({_pct(hold_pnl, DCA_CAPITAL)})"))
    print("╠" + bar + "╣")

    strategies = [
        ("MA Crossover", ma_pnl,   MA_CAPITAL),
        ("DCA",          dca_pnl,  DCA_CAPITAL),
        ("Buy & Hold",   hold_pnl, DCA_CAPITAL),
    ]
    best = max(strategies, key=lambda x: x[1] / x[2])
    for name, pnl, cap in strategies:
        marker = " ◀ WINNER" if name == best[0] else ""
        print(row(f"  {name:<14}  ${cap:.0f} → ${cap+pnl:.2f}  net {_pct(pnl, cap)}{marker}"))
    print("╚" + bar + "╝")
    print()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    rng = np.random.default_rng(RNG_SEED)

    # Generate price series once per asset (same data for all strategies)
    bars = {sym: generate_bars(sym, rng) for sym in ALL_SYMBOLS}

    ma_alloc   = MA_CAPITAL  / len(ALL_SYMBOLS)
    dca_alloc  = DCA_CAPITAL / len(ALL_SYMBOLS)

    ma_results   = [run_ma(s,   bars[s], ma_alloc)  for s in ALL_SYMBOLS]
    dca_results  = [run_dca(s,  bars[s], dca_alloc) for s in ALL_SYMBOLS]
    hold_results = [run_hold(s, bars[s], dca_alloc) for s in ALL_SYMBOLS]

    print_report(ma_results, dca_results, hold_results)


if __name__ == "__main__":
    main()
