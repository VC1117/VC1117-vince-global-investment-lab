#!/usr/bin/env python3
"""Research-only US-listed security-type triage and small-batch market-cap probe.
This is NOT a verified common-stock universe, nor a complete large-cap screen.
"""
import csv
import io
import json
import math
import os
import re
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone

import yfinance as yf

URLS = {
    "nasdaq": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "other": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}
MAX_BYTES = 3_000_000
THRESHOLD = 100_000_000_000
# Bounded deterministic pilot, not a random sample or exhaustive scan.
PILOT = ("NVDA", "MSFT", "JPM", "AAPL", "ADBE", "NKE", "GOOGL", "XOM", "BRK.B", "PLD")
SPECIAL = re.compile(r"(?:\.(?:U|W|WS|R|RT|P[A-Z]?|PR[A-Z]?)$|(?:U|W|WS|WT|R|RT)$)", re.I)

def download(source):
    request = urllib.request.Request(URLS[source], headers={"User-Agent": "VinceGlobalInvestmentLab universe research validator"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Unexpectedly large listing directory")
    data = raw.decode("utf-8-sig")
    expected = "Symbol|" if source == "nasdaq" else "ACT Symbol|"
    if not data.startswith(expected):
        raise ValueError("Unexpected listing directory response")
    return list(csv.DictReader(io.StringIO(data), delimiter="|"))

def triage(source, row):
    symbol = (row.get("Symbol") if source == "nasdaq" else row.get("ACT Symbol") or "").strip()
    if not symbol or symbol.startswith("File Creation Time"):
        return None
    if row.get("Test Issue", "").strip() != "N" or row.get("ETF", "").strip() != "N":
        return None
    if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,12}", symbol):
        return None
    name = (row.get("Security Name") or "").lower()
    if SPECIAL.search(symbol) or re.search(r"\b(warrant|rights?|units?|preferred|depositary shares)\b", name):
        status = "special_security_review"
    elif re.search(r"\b(american depositary|adr|ads|depositary receipt)\b", name):
        status = "adr_review"
    else:
        status = "common_stock_candidate_unverified"
    return symbol, status

def cap_probe(symbol):
    # Yahoo uses '-' for some class-share symbols (e.g. BRK.B -> BRK-B).
    yf_symbol = symbol.replace(".", "-")
    stock = yf.Ticker(yf_symbol)
    cap = stock.info.get("marketCap")
    if cap is None:
        cap = stock.fast_info.get("market_cap")
    if cap is None or not math.isfinite(float(cap)) or float(cap) <= 0:
        raise ValueError("Missing/invalid market capitalization")
    return {"symbol": symbol, "market_cap_bn_usd": round(float(cap) / 1e9, 2),
            "over_100bn": float(cap) > THRESHOLD}

def main():
    status = {}
    for source in URLS:
        rows = download(source)
        if len(rows) < 100:
            raise ValueError("Incomplete directory: " + source)
        for row in rows:
            result = triage(source, row)
            if result:
                symbol, kind = result
                status[symbol] = kind
    if len(status) < 1000:
        raise ValueError("Unexpectedly small universe")
    counts = dict(Counter(status.values()))
    print("TRIAGE=" + json.dumps({"symbols": len(status), "counts": counts,
        "classification_is_provisional": True}, ensure_ascii=False), flush=True)
    passed, errors = [], []
    for symbol in PILOT:
        if symbol not in status:
            errors.append({"symbol": symbol, "reason": "Not found in downloaded listing"})
            print("FAIL {} missing from directory".format(symbol), flush=True)
            continue
        try:
            result = cap_probe(symbol)
            result["security_review_status"] = status[symbol]
            passed.append(result)
            print("CAP_PROBE=" + json.dumps(result, ensure_ascii=False), flush=True)
        except Exception as exc:
            errors.append({"symbol": symbol, "reason": str(exc)[:150]})
            print("FAIL {} {}".format(symbol, str(exc)[:150]), flush=True)
        time.sleep(0.5)
    print("SUMMARY=" + json.dumps({"research_only": True, "universe_complete": False,
        "market_cap_full_scan": False, "triaged_symbols": len(status),
        "cap_pilot_tested": len(PILOT), "cap_pilot_passed": len(passed),
        "cap_pilot_eligible": sum(x["over_100bn"] for x in passed),
        "errors": errors, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "licensing_verified": False}, ensure_ascii=False), flush=True)
    if errors:
        raise SystemExit("Pilot incomplete: review missing symbols or market cap failures")

if __name__ == "__main__":
    main()
