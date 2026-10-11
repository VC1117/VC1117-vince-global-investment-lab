#!/usr/bin/env python3
"""Research-only FCN morning-brief status, derived strictly from audited coverage."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

def render(summary, run_id="unknown", scope="unknown"):
    n=summary["candidate_count"]
    done=summary["processed_unique"]
    counts=summary["counts"]
    remaining=summary["remaining"]
    if done+remaining!=n or sum(counts.values())!=done:
        raise ValueError("Inconsistent coverage counts; refusing to publish report")
    if summary.get("audit_errors"):
        raise ValueError("Audit errors present; refusing to publish report")
    lines=[
        "# FCN 美股千億市值股票池｜晨訊研究進度",
        "",
        "> 僅供內部研究；非正式市場晨訊、非投資建議，亦非可公開再散布的行情資料。",
        "",
        f"- 產出時間（UTC）：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        f"- GitHub Actions 執行：{run_id}｜模式：{scope}",
        f"- 快照識別碼：`{summary['snapshot_id']}`",
        f"- 初步普通股候選：**{n:,} 檔**（證券類型尚未驗證）",
        f"- 已完成市值查詢嘗試：**{done:,} 檔**（{done/n*100:.2f}%）" if n else "- 已完成市值查詢嘗試：0 檔",
        f"- 市值嚴格超過 US$100B：**{counts.get('eligible_over_100bn',0):,} 檔**",
        f"- 未達門檻：**{counts.get('below_threshold',0):,} 檔**",
        f"- 查詢失敗待補查：**{counts.get('failed',0):,} 檔**",
        f"- 尚未查詢：**{remaining:,} 檔**",
        f"- 全池市值查詢無失敗完成：**{'是' if summary['complete_universe_screen'] else '否'}**",
        "",
        "## 晨會使用限制",
        "",
        "- 本報表只反映已稽核的研究進度；沒有當日指數、股價、HV、MDD、IV、財報或選擇權數據，不能冒充完整市場晨訊。",
        "- 研究來源尚未完成資料再散布授權與普通股證券類型驗證；不得自動發布至網站。",
        "- 完整股票池、歷史波動與選擇權欄位需要後續資料管線與授權檢核。",
        "",
        "僅供內部參考使用 PE V.C",
        "",
    ]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--summary",type=Path,default=Path("research/coverage-summary.json"))
    p.add_argument("--out",type=Path,default=Path("research/FCN_MORNING_RESEARCH_BRIEF.md"))
    p.add_argument("--run-id",default="unknown")
    p.add_argument("--scope",default="unknown")
    a=p.parse_args()
    data=json.loads(a.summary.read_text(encoding="utf-8"))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(render(data,a.run_id,a.scope),encoding="utf-8")
    print("FCN_RESEARCH_BRIEF="+str(a.out),flush=True)
if __name__=="__main__":main()
