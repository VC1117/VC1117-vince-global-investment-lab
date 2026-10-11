#!/usr/bin/env python3
"""FCN historical volatility proof of concept. No implied volatility or coupon estimates."""
import csv, io, json, math, os, statistics, urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://stooq.com/q/d/l/?s=nvda.us&i=d"
OUT = Path("data/fcn_nvda_validation.json")

def metrics(rows):
    rows = sorted(rows, key=lambda r: r["Date"])
    dates = [r["Date"] for r in rows]
    prices = [float(r["Close"]) for r in rows]
    if len(rows) < 253 or len(set(dates)) != len(dates) or any(p <= 0 or not math.isfinite(p) for p in prices):
        raise ValueError("Need >=253 distinct trading days and finite positive close prices")
    returns = [math.log(prices[i] / prices[i-1]) for i in range(1, len(prices))]
    def hv(n):
        return round(statistics.stdev(returns[-n:]) * math.sqrt(252) * 100, 4)
    def mdd(n):
        window = prices[-n:]
        peak, worst = window[0], 0.0
        for p in window:
            peak = max(peak, p)
            worst = min(worst, p / peak - 1)
        return round(worst * 100, 4)
    return {
        "ticker": "NVDA", "last_trade_date": dates[-1], "last_close": prices[-1],
        "observations": len(rows), "hv_method": "sample stdev of daily log returns, annualized sqrt(252)",
        "mdd_method": "trailing N closing prices, chronological running peak",
        "hv_pct": {str(n): hv(n) for n in (20, 30, 60, 90, 180, 252)},
        "max_drawdown_pct": {"20": mdd(20), "90": mdd(90)},
        "return_90d_pct": round((prices[-1] / prices[-91] - 1) * 100, 4),
        "iv30_pct": None, "iv_source": None
    }

def self_test():
    sample = [{"Date": f"day{i:03d}", "Close": str(100 + i * 0.5)} for i in range(260)]
    m = metrics(sample)
    assert m["max_drawdown_pct"]["20"] == 0
    assert m["max_drawdown_pct"]["90"] == 0
    assert m["return_90d_pct"] > 0
    assert all(math.isfinite(v) for v in m["hv_pct"].values())
    declining = [{"Date": f"day{i:03d}", "Close": str(400 - i)} for i in range(260)]
    assert metrics(declining)["max_drawdown_pct"]["90"] < 0
    print("SELF TEST PASSED")

def main():
    self_test()
    if os.environ.get("FCN_FETCH_LIVE") != "1":
        print("Live download skipped. Set FCN_FETCH_LIVE=1 to validate real NVDA closes.")
        return
    req = urllib.request.Request(URL, headers={"User-Agent": "VinceInvestmentLab/0.1 validation"})
    with urllib.request.urlopen(req, timeout=25) as response:
        raw = response.read().decode("utf-8-sig")
    first_line = raw.splitlines()[0][:160] if raw.splitlines() else "(empty)"
    print("DATA_DIAGNOSTIC http_status=200 bytes={} first_line={!r}".format(len(raw.encode("utf-8")), first_line), flush=True)
    rows = list(csv.DictReader(io.StringIO(raw)))
    if not rows or not {"Date", "Close"}.issubset(rows[0]):
        raise ValueError("Unexpected CSV response; do not publish. See DATA_DIAGNOSTIC.")
    result = metrics(rows)
    result.update({"source": "Stooq public daily CSV (evaluation only)", "retrieved_utc": datetime.now(timezone.utc).isoformat(), "status": "VALIDATION_ONLY", "redistribution_approved": False})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
