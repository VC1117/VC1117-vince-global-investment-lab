#!/usr/bin/env python3
import hashlib
import json
import tempfile
from pathlib import Path
from fcn_universe_coverage import plan
from fcn_failure_diagnostics import diagnose,write_outputs

def main():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);symbols=["AAA","BBB","CCC"]
        digest=hashlib.sha256(("\n".join(symbols)+"\n").encode()).hexdigest()
        snapshot=root/"snapshot.json";manifest=root/"plan.json";results=root/"results"
        results.mkdir()
        snapshot.write_text(json.dumps({"snapshot_id":digest,"symbols":symbols,"candidate_count":3}))
        plan(snapshot,manifest,2)
        for start,rows in [(0,[{"symbol":"AAA","status":"eligible_over_100bn"},{"symbol":"BBB","status":"failed","reason":"unresolved_market_cap"}]),(2,[{"symbol":"CCC","status":"below_threshold"}])]:
            (results/("batch_%05d.json"%start)).write_text(json.dumps({"snapshot_id":digest,"start_index":start,"processed":len(rows),"statuses":rows}))
        data=diagnose(snapshot,manifest,results)
        assert len(data["failed"])==1 and data["failed"][0]["symbol"]=="BBB"
        write_outputs(data,root/"out","123")
        assert "BBB" in (root/"out"/"FCN_FAILED_SYMBOLS.csv").read_text(encoding="utf-8-sig")
        assert not json.loads((root/"out"/"FCN_FAILURE_DIAGNOSTICS.json").read_text())["actual_root_causes_verified"]
        (results/"batch_00002.json").unlink()
        try: diagnose(snapshot,manifest,results)
        except ValueError as exc: assert "Missing shards" in str(exc)
        else: raise AssertionError("Missing shard accepted")
    print("FCN_FAILURE_DIAGNOSTICS_SELF_TEST_PASSED")
if __name__=="__main__":main()
