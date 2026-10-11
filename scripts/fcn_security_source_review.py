#!/usr/bin/env python3
"""Offline review queue for FCN missing-cap symbols; no security-type guesses."""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

FIELDS=["symbol","probe_category","review_priority","issuer_legal_name","primary_exchange",
        "listing_status","security_type","security_type_evidence_url","security_type_checked_utc",
        "alternative_source_name","alternative_source_documentation_url","market_cap_definition",
        "share_class_handling","as_of_date","license_redistribution_approved",
        "source_terms_evidence_url","review_status","review_notes"]
ALLOWED={"resolved_above_threshold","resolved_below_threshold","missing_market_cap",
         "invalid_market_cap","rate_limited","access_denied","network_or_timeout",
         "provider_symbol_error","provider_parse_error","provider_unknown_error"}

def evaluate(probe_csv,probe_json):
    meta=json.loads(probe_json.read_text(encoding="utf-8"))
    if not re.fullmatch(r"[0-9a-f]{64}",str(meta.get("snapshot_id",""))):
        raise ValueError("Invalid snapshot identifier")
    with probe_csv.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=meta.get("probed_count") or len(rows)>meta.get("failed_pool_count",0):
        raise ValueError("Probe count mismatch")
    seen=set()
    counts=Counter()
    for row in rows:
        symbol=row.get("symbol","")
        category=row.get("category","")
        if not re.fullmatch(r"[A-Z0-9.^-]{1,24}",symbol) or symbol in seen:
            raise ValueError("Duplicate or invalid symbol")
        if category not in ALLOWED or row.get("attempts")!="1":
            raise ValueError("Unexpected probe row")
        seen.add(symbol);counts[category]+=1
    if dict(counts)!=meta.get("category_counts"):
        raise ValueError("Category count mismatch")
    if meta.get("security_type_verified") is not False or meta.get("licensing_verified") is not False:
        raise ValueError("Unexpected verified source claims")
    queue=[]
    for row in rows:
        cat=row["category"]
        if cat not in ("missing_market_cap","invalid_market_cap"):
            continue
        item={key:"" for key in FIELDS}
        item.update({"symbol":row["symbol"],"probe_category":cat,
                     "review_priority":"manual_security_type_and_listing",
                     "listing_status":"unverified","security_type":"unverified",
                     "license_redistribution_approved":"unverified",
                     "review_status":"pending_evidence"})
        queue.append(item)
    return meta,counts,queue

def write(meta,counts,queue,out,probe_run):
    out.mkdir(parents=True,exist_ok=True)
    with (out/"FCN_SECURITY_REVIEW_QUEUE.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader();writer.writerows(queue)
    summary={"probe_run":str(probe_run),"full_source_run":str(meta["source_run"]),
             "snapshot_id":meta["snapshot_id"],"probed_count":meta["probed_count"],
             "probe_category_counts":dict(sorted(counts.items())),
             "manual_review_queue_count":len(queue),"security_type_verified":False,
             "licensing_verified":False,"alternative_source_approved":False,
             "market_cap_reclassified":0,"publication_ready":False,"research_only":True}
    (out/"FCN_SECURITY_SOURCE_REVIEW.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# FCN｜證券類型核驗與替代市值來源評估","",
           "> **離線待查清單，不是已完成的證券類型核驗，也未查詢替代市值。**","",
           "- PR25 來源執行：`"+str(probe_run)+"`",
           "- Full 原始執行：`"+str(meta["source_run"])+"`",
           "- 診斷樣本："+str(meta["probed_count"])+" 檔",
           "- 待人工核驗（市值缺漏／無效）：**"+str(len(queue))+" 檔**","",
           "## 人工核驗工作項目","",
           "1. 以交易所官方證券名冊或監管申報核對法定發行人、交易所、上市狀態與普通股／ADR／ETF／其他證券類型。",
           "2. 核對代碼異動、股類別與公司行動；每項結論附來源 URL 與查核日期。",
           "3. 替代市值來源需確認：API/授權條款、商業使用與再散布權、時點、幣別、市值定義、股類別合併方式及更新頻率。",
           "4. 優先評估官方交易所／發行人／監管申報的識別資料；市值來源可評估具適當授權的專業行情供應商。**未宣稱任何供應商已可使用。**",
           "5. 經人工簽核且可稽核後，另設計獨立補查／回寫 PR；本 PR 不變更原始 292 檔失敗狀態。","",
           "## 候選來源評估欄位","",
           "| 評估面向 | 驗收標準 |","|---|---|",
           "| 證券識別 | 交易所、證券類型、有效上市與代碼映射可核對 |",
           "| 市值定義 | USD、時間戳、普通股股類別、總股本與自由流通市值差異明確 |",
           "| 品質 | 可追溯來源、缺值率、更新頻率、調整與歷史可用性 |",
           "| 合規 | 商業用途、衍生資料、內部展示及網站再散布授權逐項確認 |",
           "| 成本與維護 | API 限額、費率、穩定性、SLA 與錯誤處理 |","",
           "## 目前禁止事項","",
           "- 不得從 ticker 字樣猜測 ETF、ADR、下市或普通股身分。",
           "- 不得把單次診斷成功的股票直接寫回完整股票池。",
           "- 不得宣稱資料授權已通過，或把這份研究報告發布至正式網站。","",
           "僅供內部參考使用 PE V.C",""]
    (out/"FCN_SECURITY_SOURCE_REVIEW.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("FCN_SECURITY_REVIEW="+json.dumps({"probe_run":str(probe_run),"probed":meta["probed_count"],"queue":len(queue),"categories":dict(counts)},sort_keys=True),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--probe-csv",type=Path,default=Path("research/error-probe/FCN_ERROR_PROBE.csv"))
    p.add_argument("--probe-json",type=Path,default=Path("research/error-probe/FCN_ERROR_PROBE.json"))
    p.add_argument("--out",type=Path,default=Path("research/security-source-review"))
    p.add_argument("--probe-run",required=True)
    a=p.parse_args()
    write(*evaluate(a.probe_csv,a.probe_json),a.out,a.probe_run)
if __name__=="__main__":main()
