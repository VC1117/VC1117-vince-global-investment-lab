#!/usr/bin/env python3
"""PR16: deterministic research-only full-universe coverage plan and strict audit.

This does NOT screen market caps or authorize publication. It plans *all*
provisional symbols and audits batch output produced for the SAME snapshot.
"""
import argparse
import json
from collections import Counter
from pathlib import Path
from fcn_snapshot_batch_pipeline import load_snapshot

ALLOWED = {"eligible_over_100bn", "below_threshold", "failed"}

def plan(snapshot, out, size):
    data = load_snapshot(snapshot)
    symbols = data["symbols"]
    if not 1 <= size <= 25:
        raise ValueError("size must be 1..25")
    shards = [{"start": i, "size": min(size, len(symbols)-i),
               "first": symbols[i], "last": symbols[min(i+size, len(symbols))-1]}
              for i in range(0, len(symbols), size)]
    manifest = {"snapshot_id": data["snapshot_id"], "candidate_count": len(symbols),
                "batch_size": size, "batch_count": len(shards),
                "security_type_verified": False, "licensing_verified": False,
                "research_only": True, "shards": shards}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("PLAN="+json.dumps({k:v for k,v in manifest.items() if k!="shards"}), flush=True)

def audit(snapshot, manifest_file, results_dir, out):
    data = load_snapshot(snapshot)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest["snapshot_id"] != data["snapshot_id"] or manifest["candidate_count"] != len(data["symbols"]):
        raise ValueError("Manifest snapshot mismatch")
    shards = manifest["shards"]
    expected = {}
    for shard in shards:
        start, size = shard["start"], shard["size"]
        if size < 1 or start < 0 or start+size > len(data["symbols"]):
            raise ValueError("Invalid shard range")
        for symbol in data["symbols"][start:start+size]:
            if symbol in expected:
                raise ValueError("Duplicate symbol in manifest")
            expected[symbol] = start
    if set(expected) != set(data["symbols"]):
        raise ValueError("Manifest does not cover entire snapshot")
    statuses = {}
    counts = Counter()
    errors = []
    for file in sorted(results_dir.glob("batch_*.json")):
        result = json.loads(file.read_text(encoding="utf-8"))
        start = result.get("start_index")
        shard = next((s for s in shards if s["start"] == start), None)
        if result.get("snapshot_id") != data["snapshot_id"] or shard is None:
            errors.append(file.name+": snapshot or shard mismatch")
            continue
        actual = result.get("statuses", [])
        expected_batch = data["symbols"][start:start+shard["size"]]
        if [x.get("symbol") for x in actual] != expected_batch or result.get("processed") != len(expected_batch):
            errors.append(file.name+": incorrect or partial batch")
            continue
        for row in actual:
            symbol, status = row["symbol"], row.get("status")
            if symbol in statuses or status not in ALLOWED:
                errors.append(file.name+": duplicate symbol or invalid status "+symbol)
                continue
            statuses[symbol] = status
            counts[status] += 1
    remaining = len(data["symbols"])-len(statuses)
    if remaining < 0:
        raise ValueError("Invalid over-coverage")
    summary = {"snapshot_id": data["snapshot_id"], "candidate_count": len(data["symbols"]),
               "processed_unique": len(statuses), "remaining": remaining,
               "counts": dict(counts), "audit_errors": errors,
               "complete_universe_screen": remaining == 0 and not errors and counts["failed"] == 0,
               "security_type_verified": False, "licensing_verified": False,
               "publication_ready": False, "research_only": True}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("COVERAGE="+json.dumps(summary), flush=True)
    if errors:
        raise ValueError("Batch audit failed: "+ "; ".join(errors[:3]))
    return summary

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=["plan","audit"])
    p.add_argument("--snapshot",type=Path,default=Path("research/snapshot.json"))
    p.add_argument("--manifest",type=Path,default=Path("research/coverage-plan.json"))
    p.add_argument("--results",type=Path,default=Path("research/results"))
    p.add_argument("--summary",type=Path,default=Path("research/coverage-summary.json"))
    p.add_argument("--size",type=int,default=20)
    a=p.parse_args()
    if a.command=="plan": plan(a.snapshot,a.manifest,a.size)
    else: audit(a.snapshot,a.manifest,a.results,a.summary)

if __name__=="__main__":main()
