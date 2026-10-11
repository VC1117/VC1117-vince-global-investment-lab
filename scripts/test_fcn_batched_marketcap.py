#!/usr/bin/env python3
"""Research-only, bounded US-listed market-cap screening with resumable offsets.

The listing triage is provisional. This does not establish a complete common-stock
universe, a licensed market data feed, or a production-ready FCN selection.
"""
import argparse
import csv
import io
import json
import math
import re
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

URLS = (
    ("nasdaq", "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"),
    ("other", "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"),
)
SPECIAL = re.compile(r"(?:\.(?:U|W|WS|R|RT|P[A-Z]?|PR[A-Z]?)$|(?:U|W|WS|WT|R|RT)$)", re.I)
THRESHOLD = 100_000_000_000

def listing_rows(source, url):
    request = urllib.request.Request(url, headers={"User-Agent": "VinceGlobalInvestmentLab research validator"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(3_000_001)
    if len(raw) > 3_000_000:
        raise ValueError("Listing download exceeded 3 MB")
    content = raw.decode("utf-8-sig")
    expected = "Symbol|" if source == "nasdaq" else "ACT Symbol|"
    if not content.startswith(expected):
        raise ValueError("Unexpected listing source response")
    return csv.DictReader(io.StringIO(content), delimiter="|")

def universe():
    symbols = {}
    for source, url in URLS:
        for row in listing_rows(source, url):
            symbol = (row.get("Symbol") if source == "nasdaq" else row.get("ACT Symbol") or "").strip()
            if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,12}", symbol or ""):
                continue
            if row.get("Test Issue", "").strip() != "N" or row.get("ETF", "").strip() != "N":
                continue
            name = (row.get("Security Name") or "").lower()
            if SPECIAL.search(symbol) or re.search(r"\b(warrant|rights?|units?|preferred|depositary shares)\b", name):
                kind = "special_review"
            elif re.search(r"\b(american depositary|adr|ads|depositary receipt)\b", name):
                kind = "adr_review"
            else:
                kind = "common_candidate_unverified"
            symbols[symbol] = kind
    if len(symbols) < 1000:
        raise ValueError("Incomplete listing universe")
    return symbols

def market_cap(symbol):
    stock = yf.Ticker(symbol.replace(".", "-"))
    cap = stock.info.get("marketCap")
    if cap is None:
        cap = stock.fast_info.get("market_cap")
    if cap is None or not math.isfinite(float(cap)) or float(cap) <= 0:
        raise ValueError("Market capitalization missing or invalid")
    return float(cap)

def run(start, size, output):
    all_symbols = universe()
    # Stable ordering only within a frozen snapshot; live directory can change.
    candidates = sorted(symbol for symbol, kind in all_symbols.items()
                        if kind == "common_candidate_unverified")
    if start >= len(candidates):
        raise ValueError("start_index beyond current candidate list")
    batch = candidates[start:start + size]
    counts = Counter()
    failures = []
    print("UNIVERSE=" + json.dumps({
        "all_symbols": len(all_symbols), "provisional_candidates": len(candidates),
        "start_index": start, "requested_size": size, "batch_size": len(batch),
        "first_symbol": batch[0], "last_symbol": batch[-1],
        "warning": "Live directory may change between runs; offset is not a stable snapshot identifier",
    }), flush=True)
    for symbol in batch:
        try:
            cap = market_cap(symbol)
            status = "eligible_over_100bn" if cap > THRESHOLD else "below_threshold"
            counts[status] += 1
            # Research logs only; no prices or caps persisted to files/artifacts.
            print("SCREEN {} {} cap_bn={:.2f}".format(symbol, status, cap / 1e9), flush=True)
        except Exception as exc:
            counts["failed"] += 1
            failures.append({"symbol": symbol, "error": str(exc)[:150]})
            print("FAILED {} {}".format(symbol, str(exc)[:150]), flush=True)
        time.sleep(0.5)
    checkpoint = {
        "research_only": True, "no_quote_or_cap_data_persisted": True,
        "source": "Nasdaq Trader directories + unofficial yfinance fundamentals",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count_at_run": len(candidates),
        "first_symbol": batch[0], "last_symbol": batch[-1],
        "start_index": start, "processed": len(batch),
        "next_start_index": start + len(batch),
        "counts": dict(counts), "failures": failures,
        "snapshot_stable": False,
        "fully_screened": False, "licensing_verified": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("CHECKPOINT=" + json.dumps(checkpoint, ensure_ascii=False), flush=True)
    if failures:
        raise RuntimeError("{} ticker(s) failed; checkpoint saved, do not treat as complete".format(len(failures)))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--checkpoint", type=Path, default=Path("research_checkpoint/checkpoint.json"))
    args = parser.parse_args()
    if args.start_index < 0 or not 1 <= args.batch_size <= 25:
        parser.error("start-index must be >=0 and batch-size 1..25")
    run(args.start_index, args.batch_size, args.checkpoint)

if __name__ == "__main__":
    main()
