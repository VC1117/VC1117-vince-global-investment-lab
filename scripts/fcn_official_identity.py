#!/usr/bin/env python3
"""FCN official Nasdaq Trader directory cross-check; never infer common stock from ETF=N."""
import argparse
import csv
import hashlib
import io
import json
import re
import urllib.request
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

DIRECTORIES={
 "nasdaqlisted":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
 "otherlisted":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}
FIELDS=["symbol","prior_review_status","directory_match","directory_source",
        "directory_symbol","directory_security_name","directory_exchange_code",
        "directory_etf_flag","directory_test_issue","identity_finding",
        "common_stock_verified","manual_followup","source_url","retrieved_utc",
        "source_sha256"]

def read_queue(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    symbols=[r.get("symbol","") for r in rows]
    if not symbols or len(symbols)!=len(set(symbols)) or any(not re.fullmatch(r"[A-Z0-9.^-]{1,24}",s) for s in symbols):
        raise ValueError("Invalid queue symbols")
    if any(r.get("review_status")!="pending_evidence" or r.get("security_type")!="unverified" for r in rows):
        raise ValueError("Input queue must be unverified")
    return rows

def parse_directory(content,source):
    if source not in DIRECTORIES:raise ValueError("Unknown source")
    text=content.decode("utf-8-sig")
    lines=[line for line in text.splitlines() if line.strip()]
    if not lines or not lines[-1].startswith("File Creation Time:"):
        raise ValueError("Directory footer missing; refuse partial or changed file")
    reader=csv.DictReader(io.StringIO("\n".join(lines[:-1])),delimiter="|")
    required={"Symbol","Security Name","ETF","Test Issue"} if source=="nasdaqlisted" else {"ACT Symbol","Security Name","ETF","Test Issue","Exchange"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise ValueError("Unexpected directory schema")
    parsed={}
    for row in reader:
        symbol=row["Symbol" if source=="nasdaqlisted" else "ACT Symbol"].strip()
        if not symbol or not re.fullmatch(r"[A-Z0-9.^-]{1,24}",symbol):continue
        flag=row["ETF"].strip()
        test=row["Test Issue"].strip()
        if flag not in ("Y","N") or test not in ("Y","N"):
            raise ValueError("Unexpected ETF/test flag")
        if symbol in parsed:raise ValueError("Duplicate official directory symbol")
        parsed[symbol]={"source":source,"symbol":symbol,
                        "security_name":row["Security Name"].strip(),
                        "exchange":row.get("Exchange","Q").strip(),
                        "etf":flag,"test":test}
    if len(parsed)<1:raise ValueError("Empty directory")
    return parsed

def fetch_directories(fetcher=None):
    if fetcher is None:
        def fetcher(url):
            request=urllib.request.Request(url,headers={"User-Agent":"VinceGlobalInvestmentLab/1.0 research identity audit (contact via repository)"})
            with urllib.request.urlopen(request,timeout=25) as response:
                return response.read(3_000_001)
    records={};provenance={};timestamp=datetime.now(timezone.utc).isoformat()
    for source,url in DIRECTORIES.items():
        raw=fetcher(url)
        if len(raw)>3_000_000:raise ValueError("Directory exceeds safety limit")
        parsed=parse_directory(raw,source)
        provenance[source]={"url":url,"retrieved_utc":timestamp,"sha256":hashlib.sha256(raw).hexdigest(),"records":len(parsed)}
        records[source]=parsed
    return records,provenance

def match_symbol(symbol,records):
    # Exact match only. Never silently transform share-class punctuation.
    hits=[records[src][symbol] for src in DIRECTORIES if symbol in records[src]]
    if len(hits)>1:raise ValueError("Ambiguous official directory duplicate: "+symbol)
    return hits[0] if hits else None

def evaluate(queue,records,provenance):
    out=[]
    for item in queue:
        symbol=item["symbol"]
        hit=match_symbol(symbol,records)
        row={field:"" for field in FIELDS}
        row.update({"symbol":symbol,"prior_review_status":item["review_status"],
                    "directory_match":"yes" if hit else "no",
                    "common_stock_verified":"no",
                    "manual_followup":"required"})
        if hit:
            src=hit["source"];proof=provenance[src]
            row.update({"directory_source":src,"directory_symbol":hit["symbol"],
                        "directory_security_name":hit["security_name"],
                        "directory_exchange_code":hit["exchange"],
                        "directory_etf_flag":hit["etf"],
                        "directory_test_issue":hit["test"],
                        "source_url":proof["url"],"retrieved_utc":proof["retrieved_utc"],
                        "source_sha256":proof["sha256"]})
            if hit["test"]=="Y":finding="test_issue_flagged"
            elif hit["etf"]=="Y":finding="official_etf_flag_yes"
            else:finding="directory_listed_etf_no_common_stock_unverified"
            row["identity_finding"]=finding
        else:
            row["identity_finding"]="not_found_in_two_directories"
        out.append(row)
    return out

def write(rows,provenance,out,source_run):
    out.mkdir(parents=True,exist_ok=True)
    with (out/"FCN_OFFICIAL_IDENTITY_EVIDENCE.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    counts=dict(sorted(Counter(r["identity_finding"] for r in rows).items()))
    summary={"pr26_run":str(source_run),"reviewed_count":len(rows),
             "identity_findings":counts,"official_sources":provenance,
             "common_stock_verified_count":0,"market_cap_reclassified":0,
             "licensing_verified":False,"publication_ready":False,"research_only":True}
    (out/"FCN_OFFICIAL_IDENTITY_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# FCN PR27｜官方證券名錄實證交叉查核","",
           "> 本報告以 Nasdaq Trader 公開目錄的**查詢時點快照**為依據；不是普通股身分的最終確認。","",
           "- PR26 核驗清單來源 run：`"+str(source_run)+"`",
           "- 本次逐檔交叉查核："+str(len(rows))+" 檔","",
           "## 官方目錄來源與可追溯性",""]
    for source,p in provenance.items():
        lines.append("- "+source+"："+p["url"]+"；UTC "+p["retrieved_utc"]+"；SHA256 `"+p["sha256"]+"`")
    lines.extend(["","## 結果分類",""])
    for k,v in counts.items():lines.append("- `"+k+"`："+str(v)+" 檔")
    lines.extend(["","## 解讀與限制","",
                  "- `official_etf_flag_yes`：官方名錄 ETF 欄位為 Y；仍應人工核對該證券的完整分類。",
                  "- `directory_listed_etf_no_common_stock_unverified`：ETF=N **不等於普通股**；仍可能是 ADR、優先股、權證或其他證券。",
                  "- `test_issue_flagged`：測試證券標記；不可當作一般可投資股票。",
                  "- `not_found_in_two_directories`：不能據此認定下市或無效；可能有代碼映射或名錄覆蓋差異。",
                  "- 名錄反映查詢時點，並非原始市值篩選日期；來源 URL 和原始檔 SHA256 供稽核。",
                  "- 後續需以交易所官方詳情、發行人文件或 SEC 申報核實普通股、ADR、股類別及代碼異動。",
                  "- 本 PR 不取得市值、不驗證資料再散布授權、不更動原始 292 檔失敗狀態或正式網站。","",
                  "僅供內部參考使用 PE V.C"])
    (out/"FCN_OFFICIAL_IDENTITY_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("FCN_OFFICIAL_IDENTITY="+json.dumps({"reviewed":len(rows),"findings":counts,"common_stock_verified":0},sort_keys=True),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--queue",type=Path,default=Path("research/security-source-review/FCN_SECURITY_REVIEW_QUEUE.csv"))
    p.add_argument("--out",type=Path,default=Path("research/official-identity"))
    p.add_argument("--pr26-run",required=True)
    a=p.parse_args()
    queue=read_queue(a.queue)
    records,provenance=fetch_directories()
    write(evaluate(queue,records,provenance),provenance,a.out,a.pr26_run)
if __name__=="__main__":main()
