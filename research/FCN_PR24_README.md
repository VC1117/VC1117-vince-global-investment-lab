# PR #24｜292 檔失敗股票診斷與分類報告

## 用途
從第二輪 Full 成功執行 `38137632572` 的 12 個 worker artifacts 與凍結 snapshot **離線**產出 CSV、JSON、Markdown 診斷報告。不重新呼叫 yfinance，也不修改原有篩選結果。

## 執行
合併後：GitHub → Actions → **FCN failed-symbol diagnostics (offline research)** → Run workflow。預設 `source_run_id=38137632572`，可換成同一工作流程的其他已成功 Full 執行編號。來源必須成功完成、具完整 12 worker artifacts、未過期（原保留 7 天）。執行完成下載 `fcn-failure-diagnostics` artifact。

## 輸出
- `FCN_FAILED_SYMBOLS.csv`：失敗代碼、原記錄 reason、批次位置、尚待調查標籤。
- `FCN_FAILURE_DIAGNOSTICS.json`：快照、狀態統計、reason 統計、來源 run ID。
- `FCN_FAILURE_DIAGNOSTICS.md`：失敗原因的已知範圍、人工核驗與後續受控補查建議。

**重要限制：** 目前 runner 只儲存通用的 `unresolved_market_cap`，並未保留例外類型、HTTP 狀態或錯誤訊息。因此無法據此確定 292 檔的根因，更不能憑 ticker 推定退市、ETF 或限速。PR #24 是第一階段的「失敗名單與已知原因代碼盤點」，不是已驗證根因的分類。真正根因需下一階段取得可稽核的錯誤證據。資料仍為 research-only；不代表資料授權或證券類型核驗完成。

本 PR 僅新增 workflow、診斷腳本、離線測試、說明，不改網站、Page07、Page08 或既有 FCN 主工作流程。
