#!/usr/bin/env python3
"""No-network tests for FCN error probe and provenance checks."""
import csv
import json
import tempfile
from pathlib import Path
from fcn_error_probe import probe,run,save,load_failed,error_category

class FakeYF:
    def Ticker(self,s):
        class T:
            @property
            def info(self):
                if s=="BBB":raise TimeoutError("sensitive raw detail")
                if s=="CCC":return {"marketCap":None}
                return {"marketCap":101_000_000_000}
            @property
            def fast_info(self):return {"market_cap":None}
        return T()
def main():
    assert probe("AAA",FakeYF())=="resolved_above_threshold"
    assert probe("BBB",FakeYF())=="network_or_timeout"
    assert probe("CCC",FakeYF())=="missing_market_cap"
    assert error_category(Exception("429"))=="provider_unknown_error"
    assert error_category(TimeoutError("private"))=="network_or_timeout"
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);csv_path=root/"failed.csv";summary_path=root/"summary.json"
        with csv_path.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["symbol","reason"]);w.writeheader()
            for s in ("CCC","AAA","BBB"):w.writerow({"symbol":s,"reason":"unresolved_market_cap"})
        metadata={"source_run":"38137632572","snapshot_id":"a"*64,"counts":{"failed":3}}
        summary_path.write_text(json.dumps(metadata))
        symbols,summary=load_failed(csv_path,summary_path,"38137632572")
        assert symbols==["AAA","BBB","CCC"]
        rows=run(symbols,FakeYF(),12,0.5,sleeper=lambda _:None)
        save(rows,summary,root/"out","38137632572",12)
        output=json.loads((root/"out"/"FCN_ERROR_PROBE.json").read_text())
        assert output["probed_count"]==3 and output["category_counts"]["network_or_timeout"]==1
        assert "sensitive raw detail" not in (root/"out"/"FCN_ERROR_PROBE.md").read_text()
        try:load_failed(csv_path,summary_path,"123")
        except ValueError:pass
        else:raise AssertionError("source mismatch accepted")
    print("FCN_ERROR_PROBE_SELF_TEST_PASSED")
if __name__=="__main__":main()
