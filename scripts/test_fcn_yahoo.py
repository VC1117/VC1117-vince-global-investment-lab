#!/usr/bin/env python3
"""Research-only Yahoo Finance history test. Never publish or redistribute quotes."""
import json, math, os, sys
from datetime import datetime, timezone
from pathlib import Path
import yfinance as yf
from validate_fcn_volatility import metrics

def main():
    ticker = "NVDA"
    frame = yf.Ticker(ticker).history(period="2y", interval="1d", auto_adjust=True, actions=True)
    if frame.empty:
        raise RuntimeError("Yahoo returned no historical rows; no data published")
    rows = []
    for day, record in frame.iterrows():
        close = float(record["Close"])
        if math.isfinite(close) and close > 0:
            rows.append({"Date": day.strftime("%Y-%m-%d"), "Close": close})
    result = metrics(rows)
    if len(rows) < 253:
        raise ValueError("Insufficient daily closes")
    print("SOURCE=yfinance (unofficial Yahoo Finance interface); RESEARCH_ONLY; DO_NOT_PUBLISH")
    print("PRICE_BASIS=yfinance auto_adjust=True (split/dividend adjusted OHLC); verify against independent source")
    print("OBSERVATIONS={} FIRST={} LAST={} CLOSE={}".format(len(rows), rows[0]["Date"], rows[-1]["Date"], rows[-1]["Close"]))
    print("METRICS=" + json.dumps(result, ensure_ascii=False, sort_keys=True))
    if os.getenv("GITHUB_ACTIONS") != "true":
        Path("data").mkdir(exist_ok=True)
        Path("data/fcn_yahoo_research_only.json").write_text(json.dumps(result, indent=2) + "\n")

if __name__ == "__main__":
    main()
