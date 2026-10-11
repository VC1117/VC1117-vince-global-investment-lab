#!/usr/bin/env python3
"""Offline synthetic tests: complete, missing, unresolved, mixed snapshot, duplicate."""
import hashlib
import json
import tempfile
from pathlib import Path
from fcn_universe_coverage import plan, audit

def write(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data),encoding="utf-8")

def main():
    with tempfile.TemporaryDirectory() as root:
        root=Path(root)
        symbols=["AAAA","BBBB","CCCC","DDDD","EEEE"]
        digest=hashlib.sha256(("\n".join(symbols)+"\n").encode()).hexdigest()
        snapshot=root/"snapshot.json";manifest=root/"manifest.json";results=root/"results";summary=root/"summary.json"
        write(snapshot,{"symbols":symbols,"snapshot_id":digest,"candidate_count":5})
        plan(snapshot,manifest,2)
        assert len(json.loads(manifest.read_text())["shards"])==3
        def batch(start, statuses, snapshot_id=digest):
            write(results/("batch_%05d.json"%start),{"snapshot_id":snapshot_id,"start_index":start,
                 "processed":len(statuses),"statuses":[{"symbol":s,"status":st} for s,st in statuses]})
        batch(0,[("AAAA","eligible_over_100bn"),("BBBB","below_threshold")])
        batch(2,[("CCCC","below_threshold"),("DDDD","failed")])
        partial=audit(snapshot,manifest,results,summary)
        assert partial["remaining"]==1 and not partial["complete_universe_screen"]
        batch(4,[("EEEE","below_threshold")])
        unresolved=audit(snapshot,manifest,results,summary)
        assert unresolved["remaining"]==0 and not unresolved["complete_universe_screen"]
        batch(2,[("CCCC","below_threshold"),("DDDD","eligible_over_100bn")])
        assert audit(snapshot,manifest,results,summary)["complete_universe_screen"]
        batch(4,[("EEEE","below_threshold")],"wrong")
        try: audit(snapshot,manifest,results,summary)
        except ValueError: pass
        else: raise AssertionError("mixed snapshot should fail")
        batch(4,[("EEEE","below_threshold")])
        batch(0,[("AAAA","eligible_over_100bn"),("AAAA","below_threshold")])
        try: audit(snapshot,manifest,results,summary)
        except ValueError: pass
        else: raise AssertionError("duplicate batch should fail")
    print("COVERAGE_SELF_TEST_PASSED",flush=True)

if __name__=="__main__":main()
