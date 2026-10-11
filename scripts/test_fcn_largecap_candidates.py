#!/usr/bin/env python3
"""Stage 3 research-only candidate screen. NOT a complete US-listed stock universe."""
import json, math, sys, time
from collections import Counter
from datetime import datetime, timezone
import yfinance as yf
from validate_fcn_volatility import metrics

# Broad cross-sector pilot only. A licensed, regularly refreshed listing universe is still needed.
CANDIDATES = {
    "Technology": ["NVDA", "MSFT", "AAPL", "AVGO", "ORCL", "CRM", "ADBE", "AMD"],
    "Communication": ["GOOGL", "META", "NFLX", "TMUS", "VZ"],
    "Consumer": ["AMZN", "WMT", "COST", "HD", "MCD", "NKE", "TSLA"],
    "Financials": ["JPM", "BAC", "GS", "MS", "V", "MA", "BRK-B"],
    "Healthcare": ["LLY", "JNJ", "ABBV", "UNH", "MRK"],
    "Energy": ["XOM", "CVX", "COP"],
    "Industrials": ["CAT", "GE", "RTX", "UNP"],
    "Utilities": ["NEE", "SO"],
    "Materials": ["LIN", "SHW"],
    "Real Estate": ["PLD", "AMT"],
}
THRESHOLD_USD = 100_000_000_000

def main():
    screened = []
    errors = []
    latest_dates = []
    total = sum(map(len, CANDIDATES.values()))
    for sector, tickers in CANDIDATES.items():
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                # GitHub diagnostics found info.marketCap available while fast_info.market_cap was None.
                market_cap = stock.info.get("marketCap")
                if market_cap is None:
                    market_cap = stock.fast_info.get("market_cap")
                if market_cap is None or not math.isfinite(float(market_cap)) or market_cap <= 0:
                    raise ValueError("Missing/invalid market capitalization")
                eligible = float(market_cap) > THRESHOLD_USD
                row = {"ticker": ticker, "sector_tag": sector,
                       "market_cap_usd": round(float(market_cap)),
                       "eligible": eligible}
                if eligible:
                    frame = stock.history(period="2y", interval="1d", auto_adjust=True)
                    rows = [{"Date": d.strftime("%Y-%m-%d"), "Close": float(r["Close"])}
                            for d, r in frame.iterrows()
                            if math.isfinite(float(r["Close"])) and float(r["Close"]) > 0]
                    m = metrics(rows)
                    row.update({"last_trade_date": m["last_trade_date"], "observations": m["observations"],
                                "hv20_pct": m["hv_pct"]["20"], "hv252_pct": m["hv_pct"]["252"],
                                "mdd90_pct": m["max_drawdown_pct"]["90"]})
                    latest_dates.append(m["last_trade_date"])
                screened.append(row)
                print("PASS {} cap_bn={:.1f} eligible={} {}".format(
                    ticker, market_cap / 1e9, eligible,
                    "date=" + row.get("last_trade_date", "-")), flush=True)
            except Exception as exc:
                errors.append({"ticker": ticker, "reason": str(exc)[:180]})
                print("FAIL {} {}".format(ticker, str(exc)[:180]), flush=True)
            time.sleep(0.5)
    common_date = Counter(latest_dates).most_common(1)[0][0] if latest_dates else None
    stale = [r["ticker"] for r in screened if r["eligible"] and r["last_trade_date"] != common_date]
    result = {"research_only": True, "complete_us_universe": False,
              "candidate_count": total, "screened_count": len(screened),
              "eligible_count": sum(r["eligible"] for r in screened),
              "threshold_usd_exclusive": THRESHOLD_USD,
              "reference_trade_date": common_date, "stale_tickers": stale,
              "errors": errors, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
              "sector_tags": sorted(CANDIDATES)}
    print("SUMMARY=" + json.dumps(result, ensure_ascii=False), flush=True)
    print("LIMITATIONS: candidate sample only; yfinance unofficial; no licensing approval; no web publication", flush=True)
    if errors or stale or not latest_dates:
        raise SystemExit("Pilot has missing/stale data; investigate before any expansion")

if __name__ == "__main__":
    main()
