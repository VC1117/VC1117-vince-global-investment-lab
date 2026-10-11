#!/usr/bin/env python3
"""Research-only large-cap HV/MDD integration pilot; never publish fetched prices."""
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf
from validate_fcn_volatility import metrics

# Four >$100B tickers independently identified in PR #12's 80-symbol pilot.
PILOT = ("AAPL", "ABBV", "ABT", "ACN")
THRESHOLD = 100_000_000_000

def main():
    results = []
    failures = []
    for symbol in PILOT:
        try:
            ticker = yf.Ticker(symbol)
            cap = ticker.info.get("marketCap")
            if cap is None or not math.isfinite(float(cap)) or float(cap) <= THRESHOLD:
                raise ValueError("Market cap missing or no longer >$100B")
            frame = ticker.history(period="2y", interval="1d", auto_adjust=True)
            if frame.empty:
                raise ValueError("Empty adjusted daily history")
            rows = []
            for day, record in frame.iterrows():
                close = float(record["Close"])
                if not math.isfinite(close) or close <= 0:
                    raise ValueError("Invalid adjusted close")
                rows.append({"Date": day.strftime("%Y-%m-%d"), "Close": close})
            value = metrics(rows)
            value["ticker"] = symbol  # legacy metrics() defaults to NVDA
            if value["last_trade_date"] < "2026-10-09":
                raise ValueError("Stale latest trading date: " + value["last_trade_date"])
            # Print summary only; no prices, caps, or licensed data persisted to repository.
            results.append({"ticker": symbol, "last_trade_date": value["last_trade_date"],
                            "observations": value["observations"], "hv_pct": value["hv_pct"],
                            "max_drawdown_pct": value["max_drawdown_pct"],
                            "return_90d_pct": value["return_90d_pct"], "iv30_pct": None})
            print("HV_PASS {} date={} observations={} HV20={} HV252={} MDD90={}".format(
                symbol, value["last_trade_date"], value["observations"],
                value["hv_pct"]["20"], value["hv_pct"]["252"],
                value["max_drawdown_pct"]["90"]), flush=True)
        except Exception as exc:
            failures.append({"ticker": symbol, "reason": str(exc)[:160]})
            print("HV_FAIL {} {}".format(symbol, str(exc)[:160]), flush=True)
        time.sleep(1)
    report = {"status": "RESEARCH_ONLY", "data_provider": "unofficial yfinance",
              "redistribution_approved": False, "security_master_complete": False,
              "iv30_available": False, "as_of_utc": datetime.now(timezone.utc).isoformat(),
              "requested": len(PILOT), "passed": len(results), "failed": failures,
              "results": results}
    print("HV_SUMMARY=" + json.dumps(report, ensure_ascii=False), flush=True)
    if failures:
        sys.exit("Research HV integration needs review for {} symbols".format(len(failures)))

if __name__ == "__main__":
    main()
