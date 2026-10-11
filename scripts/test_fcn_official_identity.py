#!/usr/bin/env python3
"""Offline tests: official directory matching, ETF flags, fail-closed provenance."""
import csv
import tempfile
from pathlib import Path
from fcn_official_identity import parse_directory,fetch_directories,evaluate,read_queue,write

NASDAQ=b"Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\nAAA|AAA Corp|Q|N|N|100|N|N\nETF1|ETF Fund|Q|N|N|100|Y|N\nFile Creation Time: 1011202621:00\n"
OTHER=b"ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\nBBB|BBB Company|N|BBB|N|100|N|BBB\nTEST|Test Issue|A|TEST|N|100|Y|TEST\nFile Creation Time: 1011202621:00\n"
def main():
    a=parse_directory(NASDAQ,"nasdaqlisted")
    b=parse_directory(OTHER,"otherlisted")
    assert a["ETF1"]["etf"]=="Y" and b["BBB"]["exchange"]=="N"
    def fake(url):return NASDAQ if "nasdaqlisted" in url else OTHER
    records,proof=fetch_directories(fake)
    rows=evaluate([{"symbol":s,"review_status":"pending_evidence"} for s in ("AAA","ETF1","BBB","TEST","NONE")],records,proof)
    findings={r["symbol"]:r["identity_finding"] for r in rows}
    assert findings["ETF1"]=="official_etf_flag_yes"
    assert findings["AAA"]=="directory_listed_etf_no_common_stock_unverified"
    assert findings["TEST"]=="test_issue_flagged"
    assert findings["NONE"]=="not_found_in_two_directories"
    assert all(r["common_stock_verified"]=="no" for r in rows)
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        with (root/"queue.csv").open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["symbol","review_status","security_type"]);w.writeheader()
            w.writerow({"symbol":"AAA","review_status":"pending_evidence","security_type":"unverified"})
        assert len(read_queue(root/"queue.csv"))==1
        write(rows,proof,root/"out","38139524891")
        assert (root/"out"/"FCN_OFFICIAL_IDENTITY_EVIDENCE.csv").exists()
    try:parse_directory(NASDAQ.replace(b"File Creation Time:",b"Unknown Footer:"),"nasdaqlisted")
    except ValueError:pass
    else:raise AssertionError("Bad source accepted")
    print("FCN_OFFICIAL_IDENTITY_SELF_TEST_PASSED")
if __name__=="__main__":main()
