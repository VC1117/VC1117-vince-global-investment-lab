# PR #25｜292 檔精準錯誤診斷與補查策略

## 目標與邊界
獨立 GitHub Actions 工作流程，從 PR24 的已驗證失敗股票清單出發，**預設只探測 24 檔**。每檔一次受控查詢、間隔 1.5 秒；可手動選 12、24、60 或 292。採代碼排序前 N 檔，非隨機樣本，不可推論全體比例。

只記錄 `symbol`、安全類別、嘗試次數；不記錄市值、股價、原始例外、HTTP URL 或憑證。分類依據例外類型及 HTTP 狀態，**不代表已核實根因**。仍須核對交易所、普通股身分、公司行動、授權條件。

## 使用方式（合併後）
GitHub → Actions → **FCN precise failure probe (controlled research)** → Run workflow，預設 PR24 診斷 run `38138519566`，選 `probe_limit=24`。流程會驗證來源是已成功完成的 PR24 工作流程及 artifact 未過期。結果在 `fcn-precise-error-probe` artifact 中。

## 報告
- `FCN_ERROR_PROBE.csv`：股票代碼與症狀類別
- `FCN_ERROR_PROBE.json`：分類數量、來源快照、研究限制
- `FCN_ERROR_PROBE.md`：分類解釋與補查建議

## 注意
這是**新的受控資料來源查詢**，不是離線 PR24；不修改任何原始篩選狀態、網站或 Page07/08。查詢受第三方服務可用性與使用條款限制。若大量 rate limit/access denied，停止擴大。若診斷 24 檔仍不夠，先審查分類結果，再決定是否擴大或改用授權資料來源。此 PR 僅新增四個檔案，未經個別授權不合併。
