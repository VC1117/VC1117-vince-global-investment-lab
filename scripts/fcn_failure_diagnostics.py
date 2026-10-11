#!/usr/bin/env python3
"""Offline, fail-closed diagnosis of FCN batch failures; never infer root causes."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from fcn_snapshot_batch_pipeline import load_snapshot

def diagnose(snapshot_path, manifest_path, results_dir):
    snapshot=load_snapshot(snapshot_path)
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["snapshot_id"]!=snapshot["snapshot_id"] or manifest["candidate_count"]!=len(snapshot["symbols"]):
        raise ValueError("Snapshot / manifest mismatch")
    symbols=snapshot["symbols"]
    expected_starts={s["start"]:s for s in manifest["shards"]}
    found={}
    for path in sorted(results_dir.glob("batch_*.json")):
        batch=json.loads(path.read_text(encoding="utf-8"))
        start=batch.get("start_index")
        if start not in expected_starts or batch.get("snapshot_id")!=snapshot["snapshot_id"]:
            raise ValueError("Unknown shard or snapshot: "+path.name)
        shard=expected_starts[start]
        if start in found:
            raise ValueError("Duplicate shard: "+str(start))
        expected=symbols[start:start+shard["size"]]
        rows=batch.get("statuses",[])
        if [r.get("symbol") for r in rows]!=expected or batch.get("processed")!=len(expected):
            raise ValueError("Incomplete or mismatched shard: "+path.name)
        if any(r.get("status") not in ("eligible_over_100bn","below_threshold","failed") for r in rows):
            raise ValueError("Invalid status: "+path.name)
        found[start]=rows
    if set(found)!=set(expected_starts):
        raise ValueError("Missing shards: "+str(len(set(expected_starts)-set(found))))
    failed=[]
    status_counts=Counter()
    for start in sorted(found):
        for row in found[start]:
            status_counts[row["status"]]+=1
            if row["status"]=="failed":
                failed.append({"symbol":row["symbol"],"reason":row.get("reason","reason_not_recorded"),
                               "batch_start":start,"diagnosis":"unresolved_requires_investigation"})
    if sum(status_counts.values())!=len(symbols):
        raise ValueError("Inconsistent totals")
    return {"snapshot_id":snapshot["snapshot_id"],"candidate_count":len(symbols),
            "counts":dict(status_counts),"failed":failed,
            "reason_counts":dict(Counter(x["reason"] for x in failed))}

def write_outputs(data, output_dir, source_run):
    output_dir.mkdir(parents=True,exist_ok=True)
    with (output_dir/"FCN_FAILED_SYMBOLS.csv").open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=["symbol","reason","batch_start","diagnosis"])
        writer.writeheader()
        writer.writerows(data["failed"])
    summary={k:v for k,v in data.items() if k!="failed"}
    summary.update({"source_run":source_run,"actual_root_causes_verified":False,
                    "security_type_verified":False,"licensing_verified":False,
                    "research_only":True})
    (output_dir/"FCN_FAILURE_DIAGNOSTICS.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# FCN 失敗股票診斷｜內部研究","",
           "> 本報告僅根據既有批次結果離線分類，不會連線查價，不能判定真正失敗原因。","",
           "- 來源 Actions run：`"+str(source_run)+"`",
           "- 股票池候選數：**"+str(data["candidate_count"])+"**",
           "- 成功分類：**"+str(data["counts"].get("eligible_over_100bn",0)+data["counts"].get("below_threshold",0))+"**",
           "- 失敗待診斷：**"+str(len(data["failed"]))+"**","",
           "## 已記錄的失敗原因代碼",""]
    for reason,count in sorted(data["reason_counts"].items()):
        lines.append("- `"+reason+"`："+str(count)+" 檔（僅是程式記錄的通用代碼，不是已查證根因）")
    lines.extend(["","## 後續診斷優先順序","",
                  "1. 針對 CSV 逐檔核對交易所上市狀態、普通股證券類型、ticker 格式及公司行動。",
                  "2. 對少量代表性代碼進行受控資料來源測試，區分資料缺漏、代碼不支援、限速、連線與解析錯誤。",
                  "3. 記錄經核實的失敗原因與來源證據，再決定補查或人工排除；不得以代碼形狀推定證券類型。",
                  "4. 避免重複對全部 292 檔盲目重試；不得在未驗證授權前公開再散布資料。","",
                  "## 限制","",
                  "現有 runner 捕捉例外時未儲存例外類型及訊息，只留下 `unresolved_market_cap`。",
                  "因此此報告**無法**直接區分退市、特殊證券、來源缺值或 API 限速。",
                  "不得將本報告視為正式市場晨訊或公開投資資料。","",
                  "僅供內部參考使用 PE V.C",""])
    (output_dir/"FCN_FAILURE_DIAGNOSTICS.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("FCN_DIAGNOSTICS="+json.dumps({"source_run":source_run,"candidate_count":data["candidate_count"],"failed":len(data["failed"]),"reason_counts":data["reason_counts"]},sort_keys=True),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",type=Path,default=Path("research/snapshot.json"))
    p.add_argument("--manifest",type=Path,default=Path("research/coverage-plan.json"))
    p.add_argument("--results",type=Path,default=Path("research/results"))
    p.add_argument("--output",type=Path,default=Path("research/diagnostics"))
    p.add_argument("--source-run",required=True)
    a=p.parse_args()
    write_outputs(diagnose(a.snapshot,a.manifest,a.results),a.output,a.source_run)
if __name__=="__main__":
    main()
