#!/usr/bin/env python3
"""Research-only multi-sector history test. No quote publication or scheduling."""
import json, math, sys, time
from datetime import datetime, timezone
import yfinance as yf
from validate_fcn_volatility import metrics

TICKERS = ("NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "JPM", "XOM", "WMT", "LLY", "CAT")
MIN_OBSERVATIONS = 253

def main():
    results = []
    failures = []
    for ticker in TICKERS:
        try:
            frame = yf.Ticker(ticker).history(period="2y", interval="1d", auto_adjust=True)
            if frame.empty:
                raise ValueError("No daily history returned")
            rows = []
            for day, record in frame.iterrows():
                price = float(record["Close"])
                if math.isfinite(price) and price > 0:
                    rows.append({"Date": day.strftime("%Y-%m-%d"), "Close": price})
            if len(rows) < MIN_OBSERVATIONS:
                raise ValueError("Insufficient history: " + str(len(rows)))
            m = metrics(rows)
            if m["last_trade_date"] < "2026-10-09":
                raise ValueError("Potential stale history: " + m["last_trade_date"])
            results.append(m)
            print("PASS {} observations={} date={} close={:.4f} HV20={:.4f} HV252={:.4f} MDD90={:.4f}".format(
                ticker, m["observations"], m["last_trade_date"], m["last_close"],
                m["hv_pct"]["20"], m["hv_pct"]["252"], m["max_drawdown_pct"]["90"]), flush=True)
        except Exception as exc:
            failures.append({"ticker": ticker, "error": str(exc)[:200]})
            print("FAIL {} {}".format(ticker, str(exc)[:200]), flush=True)
        time.sleep(1)
    print("RESEARCH_ONLY; no quote files created or published")
    print("PRICE_BASIS=yfinance auto_adjust=True; independent verification and redistribution rights pending")
    print("SUMMARY=" + json.dumps({"tested": len(TICKERS), "passed": len(results), "failed": failures,
          "as_of_utc": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False), flush=True)
    if failures:
        raise SystemExit("Multi-ticker research validation failed for {} ticker(s)".format(len(failures)))

if __name__ == "__main__":
    main()
