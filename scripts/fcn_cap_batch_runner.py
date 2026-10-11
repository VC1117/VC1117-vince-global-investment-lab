#!/usr/bin/env python3
"""Research-only market-cap batch runner with bounded retry and no cap values saved."""
import argparse
import json
import math
import time
from pathlib import Path
from fcn_snapshot_batch_pipeline import CAP_THRESHOLD, load_snapshot

def classify(symbol, yf):
    stock = yf.Ticker(symbol.replace(".", "-"))
    cap = stock.info.get("marketCap")
    if cap is None:
        cap = stock.fast_info.get("market_cap")
    if cap is None or not math.isfinite(float(cap)) or float(cap) <= 0:
        raise ValueError("Market cap missing or invalid")
    return "eligible_over_100bn" if float(cap) > CAP_THRESHOLD else "below_threshold"

def run(snapshot, manifest_path, results, worker, workers, attempts, pause, yf, limit_shards=None, retry_failed=False):
    data = load_snapshot(snapshot)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["snapshot_id"] != data["snapshot_id"]:
        raise ValueError("Snapshot mismatch")
    shards = manifest["shards"][:limit_shards] if limit_shards is not None else manifest["shards"]
    if not (0 <= worker < workers <= 32) or not (1 <= attempts <= 3):
        raise ValueError("Invalid worker or retry configuration")
    results.mkdir(parents=True, exist_ok=True)
    for shard in shards[worker::workers]:
        start = shard["start"]
        path = results / ("batch_%05d.json" % start)
        expected = data["symbols"][start:start+shard["size"]]
        if path.exists():
            old = json.loads(path.read_text(encoding="utf-8"))
            if old.get("snapshot_id") != data["snapshot_id"] or [x.get("symbol") for x in old.get("statuses",[])] != expected:
                raise ValueError("Existing batch mismatch: "+str(path))
            if not retry_failed or not any(row["status"] == "failed" for row in old["statuses"]):
                print("SKIP_EXISTING",start,flush=True)
                continue
            old_statuses = {row["symbol"]: row for row in old["statuses"]}
        else:
            old_statuses = {}
        statuses = []
        for symbol in expected:
            if symbol in old_statuses and old_statuses[symbol]["status"] != "failed":
                statuses.append(old_statuses[symbol])
                continue
            status = None
            for attempt in range(attempts):
                try:
                    status = classify(symbol,yf)
                    break
                except Exception:
                    if attempt+1 < attempts:
                        time.sleep(pause*(attempt+1))
            statuses.append({"symbol":symbol,"status":status or "failed",
                             **({"reason":"unresolved_market_cap"} if status is None else {})})
            time.sleep(pause)
        counts = {key:sum(x["status"]==key for x in statuses) for key in ("eligible_over_100bn","below_threshold","failed")}
        result={"snapshot_id":data["snapshot_id"],"start_index":start,
                "next_start_index":start+len(expected),"processed":len(expected),
                "counts":counts,"statuses":statuses,"research_only":True}
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        tmp.replace(path)
        print("BATCH_RESULT",start,json.dumps(counts),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",type=Path,default=Path("research/snapshot.json"))
    p.add_argument("--manifest",type=Path,default=Path("research/coverage-plan.json"))
    p.add_argument("--results",type=Path,default=Path("research/results"))
    p.add_argument("--worker",type=int,required=True)
    p.add_argument("--workers",type=int,required=True)
    p.add_argument("--attempts",type=int,default=2)
    p.add_argument("--pause",type=float,default=0.5)
    p.add_argument("--limit-shards",type=int,default=None)
    p.add_argument("--retry-failed",action="store_true")
    a=p.parse_args()
    if not 0.25 <= a.pause <= 5:
        p.error("pause must be 0.25..5 seconds")
    import yfinance as yf
    if a.limit_shards is not None and a.limit_shards < 1:
        p.error("limit-shards must be positive")
    run(a.snapshot,a.manifest,a.results,a.worker,a.workers,a.attempts,a.pause,yf,a.limit_shards,a.retry_failed)

if __name__=="__main__":main()
