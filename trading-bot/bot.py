#!/usr/bin/env python3
"""
Trading bot — runs on a fixed interval, evaluates MA crossover signals,
and places paper/testnet orders on Alpaca, Binance, and Coinbase.
"""
import logging
import sys
from apscheduler.schedulers.blocking import BlockingScheduler

import config
from strategy import compute_signal, Signal
from models.trade import Side
from brokers.alpaca_client import AlpacaClient
from brokers.binance_client import BinanceClient
from brokers.coinbase_client import CoinbaseClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("bot")


def _signal_to_side(signal: Signal) -> Side | None:
    if signal == Signal.BUY:
        return Side.BUY
    if signal == Signal.SELL:
        return Side.SELL
    return None


def run_alpaca(client: AlpacaClient) -> None:
    for symbol in config.STOCK_SYMBOLS:
        try:
            df = client.get_bars(symbol, config.BAR_LIMIT)
            signal = compute_signal(df, config.FAST_MA, config.SLOW_MA)
            logger.info("Alpaca %s → %s", symbol, signal.value.upper())

            if signal == Signal.HOLD:
                continue

            position = client.get_position(symbol)
            if signal == Signal.SELL and position <= 0:
                logger.info("No position in %s, skipping SELL", symbol)
                continue

            trade = client.place_order(symbol, _signal_to_side(signal), config.STOCK_QTY)
            logger.info("Executed: %s", trade)
        except Exception as exc:
            logger.error("Alpaca error for %s: %s", symbol, exc)


def run_binance(client: BinanceClient) -> None:
    for symbol in config.BINANCE_SYMBOLS:
        try:
            df = client.get_bars(symbol, config.BAR_LIMIT)
            signal = compute_signal(df, config.FAST_MA, config.SLOW_MA)
            logger.info("Binance %s → %s", symbol, signal.value.upper())

            if signal == Signal.HOLD:
                continue

            trade = client.place_order(symbol, _signal_to_side(signal), config.CRYPTO_QTY)
            logger.info("Executed: %s", trade)
        except Exception as exc:
            logger.error("Binance error for %s: %s", symbol, exc)


def run_coinbase(client: CoinbaseClient) -> None:
    for symbol in config.COINBASE_SYMBOLS:
        try:
            df = client.get_bars(symbol, config.BAR_LIMIT)
            signal = compute_signal(df, config.FAST_MA, config.SLOW_MA)
            logger.info("Coinbase %s → %s", symbol, signal.value.upper())

            if signal == Signal.HOLD:
                continue

            trade = client.place_order(symbol, _signal_to_side(signal), config.CRYPTO_QTY)
            logger.info("Executed: %s", trade)
        except Exception as exc:
            logger.error("Coinbase error for %s: %s", symbol, exc)


def tick() -> None:
    logger.info("=== Bot tick started ===")
    alpaca = AlpacaClient()
    binance = BinanceClient()
    coinbase = CoinbaseClient()

    run_alpaca(alpaca)
    run_binance(binance)
    run_coinbase(coinbase)
    logger.info("=== Bot tick complete ===")


if __name__ == "__main__":
    logger.info("Starting trading bot (paper/testnet mode)")
    logger.info(
        "Stocks: %s | Binance: %s | Coinbase: %s",
        config.STOCK_SYMBOLS,
        config.BINANCE_SYMBOLS,
        config.COINBASE_SYMBOLS,
    )

    # Run once immediately, then on schedule
    tick()

    scheduler = BlockingScheduler()
    scheduler.add_job(tick, "interval", minutes=config.RUN_INTERVAL_MINUTES)
    logger.info("Scheduler started — running every %d minutes", config.RUN_INTERVAL_MINUTES)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
