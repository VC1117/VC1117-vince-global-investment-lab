#!/usr/bin/env python3
"""Offline tests for fail-closed FCN security review queue."""
import csv
import json
import tempfile
from pathlib import Path
from fcn_security_source_review import evaluate,write

def main():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);p=root/"probe.csv";j=root/"probe.json"
        with p.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["symbol","category","attempts"]);w.writeheader()
            for sym,cat in [("AAA","missing_market_cap"),("BBB","resolved_below_threshold"),("CCC","invalid_market_cap")]:
                w.writerow({"symbol":sym,"category":cat,"attempts":1})
        data={"source_run":"38137632572","snapshot_id":"a"*64,"probed_count":3,"failed_pool_count":292,
              "category_counts":{"missing_market_cap":1,"resolved_below_threshold":1,"invalid_market_cap":1},
              "security_type_verified":False,"licensing_verified":False}
        j.write_text(json.dumps(data))
        meta,counts,queue=evaluate(p,j)
        assert [x["symbol"] for x in queue]==["AAA","CCC"]
        assert all(x["security_type"]=="unverified" for x in queue)
        write(meta,counts,queue,root/"out","38139109951")
        result=json.loads((root/"out"/"FCN_SECURITY_SOURCE_REVIEW.json").read_text())
        assert result["manual_review_queue_count"]==2 and not result["alternative_source_approved"]
        data["category_counts"]["missing_market_cap"]=2
        j.write_text(json.dumps(data))
        try:evaluate(p,j)
        except ValueError:pass
        else:raise AssertionError("Tampered counts accepted")
    print("FCN_SECURITY_SOURCE_REVIEW_SELF_TEST_PASSED")
if __name__=="__main__":main()
