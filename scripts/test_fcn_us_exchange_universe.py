#!/usr/bin/env python3
"""Research-only U.S. exchange listing discovery; never publish market data."""
import csv
import io
import json
import re
import urllib.request
from collections import Counter
from datetime import datetime, timezone

SOURCES = {
    "nasdaq": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "other": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}
MAX_BYTES = 3_000_000

def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "VinceGlobalInvestmentLab research universe validator"})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Oversized listing file")
        text = raw.decode("utf-8-sig")
    if not text.startswith(("Symbol|", "ACT Symbol|")):
        raise ValueError("Unexpected response, likely not a listing file")
    return list(csv.DictReader(io.StringIO(text), delimiter="|"))

def parse(source, records):
    out = {}
    for row in records:
        symbol = (row.get("Symbol") if source == "nasdaq" else row.get("ACT Symbol") or "").strip()
        if not symbol or symbol.startswith("File Creation Time"):
            continue
        if row.get("Test Issue", "").strip() != "N":
            continue
        if row.get("ETF", "").strip() != "N":
            continue
        if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,12}", symbol):
            continue
        # Other Listed includes NYSE, NYSE American, NYSE Arca, etc.
        out[symbol] = {"symbol": symbol, "source": source,
                       "exchange_code": row.get("Exchange", "Q" if source == "nasdaq" else "")}
    return out

def main():
    combined = {}
    source_counts = {}
    for source, url in SOURCES.items():
        records = download(url)
        parsed = parse(source, records)
        if not parsed or len(parsed) < 100:
            raise ValueError("Unusually few symbols from " + source)
        source_counts[source] = {"raw_rows": len(records), "common_stock_candidates": len(parsed)}
        combined.update(parsed)
    if len(combined) < 1000:
        raise ValueError("Incomplete exchange listing universe")
    summary = {
        "research_only": True,
        "market_cap_screened": False,
        "fully_verified_us_common_stock_universe": False,
        "symbols_discovered": len(combined),
        "source_counts": source_counts,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "sample_symbols": sorted(combined)[:12],
        "known_limitations": [
            "Exchange directory is NOT a vetted common-stock-only master list",
            "ETF/test flags excluded, but preferred shares, warrants, units, ADRs and funds may remain",
            "US exchange listing does not mean US incorporation",
            "No market-cap eligibility inferred; authoritative security-type filtering still required",
            "Yahoo market cap and quote redistribution permissions unverified"
        ]
    }
    print("SUMMARY=" + json.dumps(summary, ensure_ascii=False), flush=True)
    print("RESEARCH_ONLY: no universe files, quotes or web artifacts written", flush=True)

if __name__ == "__main__":
    main()
