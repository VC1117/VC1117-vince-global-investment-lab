# PR #27｜20 檔股票證券身分實證查核與來源追溯

## 核心改變
本 PR **實際查詢官方 Nasdaq Trader 證券名錄**，不是僅再產生一份空白清單。工作流程從 PR26 run `38139524891` 的 artifact 取得 20 檔 `pending_evidence` 股票，逐檔以原始 ticker 精確比對官方兩份名錄：

- Nasdaq Listed： https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt
- Other Listed： https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt

保存官方目錄來源 URL、UTC 查詢時點、原始檔 SHA256、目錄中的證券名稱、交易所代碼、ETF 與測試證券旗標，作為可稽核證據。網路失敗或來源格式異常則整個工作失敗，不輸出假資料。

## 重要的查核界線
- **ETF=Y**：官方目錄明示 ETF 旗標；仍應核對實際證券種類。
- **ETF=N 不等於普通股**：可能是 ADR、優先股或其他類型，因此 `common_stock_verified` 一律為 `no`。
- **找不到名錄**：不等於下市；仍需檢查代碼異動、覆蓋範圍與其他官方資料。
- 這是**目前名錄快照**，不能直接代表原始市值篩選日期的歷史上市狀態。
- 不查市值、不判定超過千億門檻、不確認授權、不修改 292 檔分類或網站。

## 使用
合併後：GitHub Actions → **FCN official identity evidence (20-symbol research)** → Run workflow，選 `main`，預設 `review_run_id=38139524891`。

Artifact `fcn-official-identity-evidence`：
1. `FCN_OFFICIAL_IDENTITY_EVIDENCE.csv`：逐檔官方名錄證據及核驗限制。
2. `FCN_OFFICIAL_IDENTITY_SUMMARY.json`：來源檔 SHA256、查詢時間、結果計數。
3. `FCN_OFFICIAL_IDENTITY_REPORT.md`：結果與下一階段人工確認建議。

## 後續
查到目錄 ETF=N 但證券類型未確認者，須再用交易所詳情、發行人或 SEC 申報確認普通股／ADR／其他；未經人工核對不可更新正式篩選名單。此 PR 僅新增四個檔案，保持獨立研究流程。
