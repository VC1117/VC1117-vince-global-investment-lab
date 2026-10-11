#!/usr/bin/env python3
"""Offline deterministic tests of the bounded-retry batch executor."""
import hashlib
import json
import tempfile
from pathlib import Path
from fcn_universe_coverage import plan,audit
from fcn_cap_batch_runner import run

class FakeTicker:
    def __init__(self,sym,counts):
        self.sym=sym;self.counts=counts
    @property
    def info(self):
        self.counts[self.sym]=self.counts.get(self.sym,0)+1
        if self.sym=="BBB" and self.counts[self.sym]==1:
            raise ValueError("transient")
        if self.sym=="CCC":
            raise ValueError("missing")
        return {"marketCap":{"AAA":101_000_000_000,"BBB":99_000_000_000}.get(self.sym)}
class FakeYF:
    def __init__(self):self.counts={}
    def Ticker(self,s):return FakeTicker(s,self.counts)

def main():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);symbols=["AAA","BBB","CCC"]
        digest=hashlib.sha256(("\n".join(symbols)+"\n").encode()).hexdigest()
        snapshot=root/"snapshot.json";manifest=root/"manifest.json";results=root/"results"
        snapshot.write_text(json.dumps({"snapshot_id":digest,"symbols":symbols,"candidate_count":3}),encoding="utf-8")
        plan(snapshot,manifest,2)
        fake=FakeYF()
        run(snapshot,manifest,results,0,2,2,0,fake)
        run(snapshot,manifest,results,1,2,2,0,fake)
        rows=[json.loads(p.read_text()) for p in sorted(results.glob("batch_*.json"))]
        assert [x["status"] for r in rows for x in r["statuses"]]==["eligible_over_100bn","below_threshold","failed"]
        assert fake.counts["BBB"]==2 and fake.counts["CCC"]==2
        summary=audit(snapshot,manifest,results,root/"summary.json")
        assert summary["remaining"]==0 and not summary["complete_universe_screen"]
        before=dict(fake.counts)
        run(snapshot,manifest,results,0,2,2,0,fake)
        assert fake.counts==before
    print("CAP_BATCH_RUNNER_SELF_TEST_PASSED",flush=True)
if __name__=="__main__":main()
