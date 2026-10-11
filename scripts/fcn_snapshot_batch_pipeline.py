#!/usr/bin/env python3
"""Research-only immutable-per-run exchange universe snapshot and automated cap batches.

Not a validated common-stock master, not a completed >$100B universe, and not
licensed for market-data redistribution. No market cap figures are persisted.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import re
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

URLS = {
    "nasdaq": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "other": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}
SPECIAL = re.compile(r"(?:\.(?:U|W|WS|R|RT|P[A-Z]?|PR[A-Z]?)$|(?:U|W|WS|WT|R|RT)$)", re.I)
CAP_THRESHOLD = 100_000_000_000

def fetch(source):
    req = urllib.request.Request(URLS[source], headers={"User-Agent": "VinceGlobalInvestmentLab research validation"})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read(3_000_001)
    if len(raw) > 3_000_000:
        raise ValueError("Listing directory oversized")
    content = raw.decode("utf-8-sig")
    if not content.startswith("Symbol|" if source == "nasdaq" else "ACT Symbol|"):
        raise ValueError("Listing directory returned unexpected format")
    return csv.DictReader(io.StringIO(content), delimiter="|")

def build_snapshot(path):
    universe = {}
    for source in URLS:
        for row in fetch(source):
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
            universe[symbol] = kind
    if len(universe) < 1000:
        raise ValueError("Suspiciously small exchange universe")
    candidates = sorted(symbol for symbol, kind in universe.items() if kind == "common_candidate_unverified")
    digest = hashlib.sha256(("\n".join(candidates) + "\n").encode()).hexdigest()
    data = {"snapshot_id": digest, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
            "candidate_count": len(candidates), "universe_count": len(universe),
            "classification_counts": dict(Counter(universe.values())),
            "security_type_verified": False, "symbols": candidates}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print("SNAPSHOT=" + json.dumps({k: v for k, v in data.items() if k != "symbols"}), flush=True)

def load_snapshot(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    symbols = data["symbols"]
    digest = hashlib.sha256(("\n".join(symbols) + "\n").encode()).hexdigest()
    if digest != data["snapshot_id"] or symbols != sorted(set(symbols)):
        raise ValueError("Snapshot checksum or order mismatch")
    return data

def screen(path, start, batch_size, result_dir):
    import yfinance as yf
    data = load_snapshot(path)
    symbols = data["symbols"][start:start + batch_size]
    if not symbols:
        raise ValueError("No symbols in requested batch")
    counts = Counter()
    statuses = []
    for symbol in symbols:
        try:
            stock = yf.Ticker(symbol.replace(".", "-"))
            cap = stock.info.get("marketCap")
            if cap is None:
                cap = stock.fast_info.get("market_cap")
            if cap is None or not math.isfinite(float(cap)) or float(cap) <= 0:
                raise ValueError("Market capitalization unavailable")
            status = "eligible_over_100bn" if float(cap) > CAP_THRESHOLD else "below_threshold"
            counts[status] += 1
            statuses.append({"symbol": symbol, "status": status})
            print("SCREEN {} {}".format(symbol, status), flush=True)
        except Exception as exc:
            counts["failed"] += 1
            statuses.append({"symbol": symbol, "status": "failed", "reason": str(exc)[:120]})
            print("FAILED {} {}".format(symbol, str(exc)[:120]), flush=True)
        time.sleep(0.5)
    result = {"snapshot_id": data["snapshot_id"], "start_index": start,
              "next_start_index": start + len(symbols), "processed": len(symbols),
              "counts": dict(counts), "statuses": statuses, "research_only": True}
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / ("batch_%05d.json" % start)).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("BATCH=" + json.dumps({k: v for k, v in result.items() if k != "statuses"}), flush=True)
    # Missing fundamentals are a recorded data-quality exception, not a crash.
    # A separate completeness gate still prevents claiming a full clean screen.
    if counts["failed"]:
        print("DATA_QUALITY_WARNING: {} unresolved tickers; batch output retained".format(counts["failed"]), flush=True)

def summarize(path, result_dir):
    data = load_snapshot(path)
    files = sorted(result_dir.glob("batch_*.json"))
    results = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    if not results:
        raise ValueError("No batch results")
    seen = set()
    counts = Counter()
    for result in results:
        if result["snapshot_id"] != data["snapshot_id"]:
            raise ValueError("Mixed snapshots detected")
        expected = data["symbols"][result["start_index"]:result["next_start_index"]]
        actual = [x["symbol"] for x in result["statuses"]]
        if expected != actual or any(x in seen for x in actual):
            raise ValueError("Overlapping or mismatched batches")
        seen.update(actual)
        counts.update(result["counts"])
    summary = {"snapshot_id": data["snapshot_id"], "candidate_count": data["candidate_count"],
               "processed_unique": len(seen), "remaining": data["candidate_count"] - len(seen),
               "batch_files": len(files), "counts": dict(counts),
               "complete_universe_screen": len(seen) == data["candidate_count"] and counts["failed"] == 0,
               "security_type_verified": False, "licensing_verified": False, "research_only": True}
    (result_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("SUMMARY=" + json.dumps(summary), flush=True)
    if counts["failed"]:
        print("DATA_QUALITY_WARNING: {} unresolved tickers; complete_universe_screen=false".format(counts["failed"]), flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["snapshot", "screen", "summarize"])
    parser.add_argument("--snapshot", type=Path, default=Path("research/snapshot.json"))
    parser.add_argument("--results", type=Path, default=Path("research/results"))
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--size", type=int, default=20)
    args = parser.parse_args()
    if args.start < 0 or not 1 <= args.size <= 25:
        parser.error("start must be >=0, size must be 1..25")
    if args.command == "snapshot":
        build_snapshot(args.snapshot)
    elif args.command == "screen":
        screen(args.snapshot, args.start, args.size, args.results)
    else:
        summarize(args.snapshot, args.results)

if __name__ == "__main__":
    main()
