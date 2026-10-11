#!/usr/bin/env python3
"""Controlled research-only FCN error probe. Never persist prices, market caps, or raw exceptions."""
import argparse
import csv
import json
import math
import re
import time
from collections import Counter
from pathlib import Path

CATEGORIES={"resolved_above_threshold","resolved_below_threshold","missing_market_cap",
            "invalid_market_cap","rate_limited","access_denied","network_or_timeout",
            "provider_symbol_error","provider_parse_error","provider_unknown_error"}
THRESHOLD=100_000_000_000

def error_category(exc):
    name=type(exc).__name__.lower()
    # Use only exception type or explicit HTTP status properties; never persist message/URL.
    status=getattr(exc,"status_code",None)
    if status is None:
        response=getattr(exc,"response",None)
        status=getattr(response,"status_code",None)
    if status==429 or "ratelimit" in name or "toomanyrequests" in name:
        return "rate_limited"
    if status in (401,403) or "unauthorized" in name or "forbidden" in name:
        return "access_denied"
    if "timeout" in name or "connection" in name or "network" in name:
        return "network_or_timeout"
    if "ticker" in name or "symbol" in name or "delisted" in name:
        return "provider_symbol_error"
    if "json" in name or "decode" in name or "parse" in name:
        return "provider_parse_error"
    return "provider_unknown_error"

def probe(symbol,yf):
    ticker=yf.Ticker(symbol.replace(".","-"))
    try:
        info=ticker.info
        cap=info.get("marketCap") if isinstance(info,dict) else None
        if cap is None:
            cap=ticker.fast_info.get("market_cap")
        if cap is None:
            return "missing_market_cap"
        try:
            numeric=float(cap)
        except (TypeError,ValueError,OverflowError):
            return "invalid_market_cap"
        if not math.isfinite(numeric) or numeric<=0:
            return "invalid_market_cap"
        return "resolved_above_threshold" if numeric>THRESHOLD else "resolved_below_threshold"
    except Exception as exc:
        return error_category(exc)

def load_failed(csv_path,summary_path,source_run):
    summary=json.loads(summary_path.read_text(encoding="utf-8"))
    if str(summary.get("source_run"))!=str(source_run) or not re.fullmatch(r"[0-9a-f]{64}",str(summary.get("snapshot_id",""))):
        raise ValueError("Source run / snapshot provenance mismatch")
    with csv_path.open(newline="",encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    if not rows or len(rows)!=summary["counts"].get("failed"):
        raise ValueError("Failed CSV count mismatch")
    symbols=[r["symbol"] for r in rows]
    if len(set(symbols))!=len(symbols) or any(not re.fullmatch(r"[A-Z0-9.^-]{1,24}",s) for s in symbols):
        raise ValueError("Invalid or duplicate symbol")
    if any(r.get("reason") not in ("unresolved_market_cap","reason_not_recorded") for r in rows):
        raise ValueError("Unexpected original reason")
    return sorted(symbols),summary

def run(symbols,yf,limit,pause,attempts=1,sleeper=time.sleep):
    if limit not in (12,24,60,292) or not (0.5<=pause<=5) or attempts!=1:
        raise ValueError("Invalid bounded probe configuration")
    selected=symbols[:limit]
    rows=[]
    for symbol in selected:
        category=probe(symbol,yf)
        if category not in CATEGORIES:
            raise ValueError("Unexpected category")
        rows.append({"symbol":symbol,"category":category,"attempts":1})
        sleeper(pause)
    return rows

def save(rows,summary,out,source_run,limit):
    out.mkdir(parents=True,exist_ok=True)
    with (out/"FCN_ERROR_PROBE.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["symbol","category","attempts"])
        writer.writeheader();writer.writerows(rows)
    counts=dict(sorted(Counter(x["category"] for x in rows).items()))
    payload={"source_run":str(source_run),"snapshot_id":summary["snapshot_id"],
             "failed_pool_count":summary["counts"]["failed"],"requested_limit":limit,
             "probed_count":len(rows),"category_counts":counts,
             "market_cap_values_stored":False,"raw_exceptions_stored":False,
             "root_cause_verified":False,"security_type_verified":False,
             "licensing_verified":False,"publication_ready":False,"research_only":True}
    (out/"FCN_ERROR_PROBE.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# FCN 失敗股票｜精準診斷研究報告","",
           "> 研究用途；單次受控再查詢的症狀分類，**不等同已核實根因**。","",
           "- 原始 Full run：`"+str(source_run)+"`",
           "- 原失敗池："+str(payload["failed_pool_count"])+" 檔",
           "- 本次抽查："+str(len(rows))+" 檔（按代碼排序取前 N 檔，**非隨機代表性樣本**）","",
           "## 查詢症狀分類",""]
    for key,n in counts.items():lines.append("- `"+key+"`："+str(n)+" 檔")
    lines.extend(["","## 補查策略","",
                  "- `resolved_*`：表示本次成功取得市值分類；須以完整快照與獨立稽核核對後，才可更新原始分類。",
                  "- `missing_market_cap` / `invalid_market_cap`：先核實公司、交易所、普通股身分與資料欄位，再選擇合法替代來源。",
                  "- `rate_limited` / `access_denied`：停止擴大查詢，檢查來源使用限制與授權；勿透過密集重試規避限制。",
                  "- `network_or_timeout`：核實網路環境及服務狀態後，以低頻受控方式重試。",
                  "- `provider_symbol_error`：人工核對股票代碼、公司行動與上市狀態。",
                  "- `provider_parse_error` / `provider_unknown_error`：檢查相容性，必要時再設計更細緻且不暴露敏感內容的錯誤分類。","",
                  "## 研究限制","",
                  "沒有保存市值、原始例外文字、API URL 或價格；例外分類只根據類型與可用 HTTP 狀態。",
                  "來源資料可用性及再散布授權均未驗證；不得更新網站、正式股票池或公開發布。","",
                  "僅供內部參考使用 PE V.C",""])
    (out/"FCN_ERROR_PROBE.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("FCN_ERROR_PROBE="+json.dumps({"source_run":str(source_run),"probed":len(rows),"categories":counts},sort_keys=True),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",type=Path,default=Path("research/diagnostics/FCN_FAILED_SYMBOLS.csv"))
    p.add_argument("--summary",type=Path,default=Path("research/diagnostics/FCN_FAILURE_DIAGNOSTICS.json"))
    p.add_argument("--out",type=Path,default=Path("research/error-probe"))
    p.add_argument("--source-run",required=True)
    p.add_argument("--limit",type=int,choices=(12,24,60,292),default=24)
    p.add_argument("--pause",type=float,default=1.5)
    a=p.parse_args()
    symbols,summary=load_failed(a.csv,a.summary,a.source_run)
    import yfinance as yf
    save(run(symbols,yf,a.limit,a.pause),summary,a.out,a.source_run,a.limit)
if __name__=="__main__":main()
