#!/usr/bin/env python3
"""Offline brief rendering and fail-closed audit validation."""
from fcn_morning_research_brief import render

def main():
    s={"snapshot_id":"offline","candidate_count":4,"processed_unique":3,"remaining":1,"counts":{"eligible_over_100bn":1,"below_threshold":1,"failed":1},"audit_errors":[],"complete_universe_screen":False}
    t=render(s,"123","pilot")
    assert "3 檔" in t and "1 檔" in t and "123" in t
    assert "非正式市場晨訊" in t
    s["remaining"]=0
    try: render(s)
    except ValueError: pass
    else: raise AssertionError("inconsistent coverage must fail")
    print("FCN_BRIEF_SELF_TEST_PASSED")
if __name__=="__main__":main()
