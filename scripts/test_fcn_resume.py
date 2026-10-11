#!/usr/bin/env python3
"""Offline regression: resume retries failures without re-querying successful symbols."""
import json, tempfile
from pathlib import Path
from fcn_universe_coverage import plan, audit
from fcn_cap_batch_runner import run

class Ticker:
    def __init__(self, symbol, api):
        self.symbol=symbol;self.api=api
    @property
    def info(self):
        self.api.calls[self.symbol]=self.api.calls.get(self.symbol,0)+1
        if self.symbol=="BBB" and self.api.calls[self.symbol]==1:
            raise ValueError("temporary")
        return {"marketCap":120_000_000_000 if self.symbol=="AAA" else 80_000_000_000}
class API:
    def __init__(self): self.calls={}
    def Ticker(self,s): return Ticker(s,self)

def main():
    with tempfile.TemporaryDirectory() as td:
        d=Path(td);snap=d/"snapshot.json";manifest=d/"manifest.json";out=d/"results"
        snap.write_text(json.dumps({"snapshot_id":"offline-1","symbols":["AAA","BBB"]}))
        plan(snap,manifest,2)
        api=API()
        run(snap,manifest,out,0,1,1,0,api)
        assert api.calls=={"AAA":1,"BBB":1}
        assert audit(snap,manifest,out,d/"summary.json")["counts"]["failed"]==1
        run(snap,manifest,out,0,1,1,0,api,retry_failed=True)
        assert api.calls=={"AAA":1,"BBB":2}
        assert audit(snap,manifest,out,d/"summary.json")["complete_universe_screen"]
        run(snap,manifest,out,0,1,1,0,api,retry_failed=True)
        assert api.calls=={"AAA":1,"BBB":2}
    print("FCN_RESUME_SELF_TEST_PASSED")
if __name__=="__main__":main()
