#!/usr/bin/env python3
"""Research-only diagnostics for Yahoo market-cap fields; no data publication."""
import json
import yfinance as yf

for symbol in ("NVDA", "MSFT", "JPM"):
    print("TICKER=" + symbol, flush=True)
    stock = yf.Ticker(symbol)
    for label, getter in (
        ("fast_info.market_cap", lambda: stock.fast_info.get("market_cap")),
        ("fast_info.shares", lambda: stock.fast_info.get("shares")),
        ("fast_info.last_price", lambda: stock.fast_info.get("last_price")),
        ("info.marketCap", lambda: stock.info.get("marketCap")),
        ("info.sharesOutstanding", lambda: stock.info.get("sharesOutstanding")),
    ):
        try:
            value = getter()
            print("FIELD {} {}={}".format(symbol, label, value), flush=True)
        except Exception as exc:
            print("FIELD_ERROR {} {} {}: {}".format(symbol, label, type(exc).__name__, str(exc)[:200]), flush=True)
print("RESEARCH_ONLY: no data saved, published, or used to infer eligibility", flush=True)
