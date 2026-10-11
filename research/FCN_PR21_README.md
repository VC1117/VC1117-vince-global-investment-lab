# PR #21｜可稽核 FCN 研究晨訊與恢復紀錄

這是**內部研究進度晨訊**，並非完成的全球市場晨訊或正式行情發布。

1. GitHub Actions → **FCN automated market-cap screening** → Run workflow。
2. 驗證恢復：`scope=pilot`、`resume_run_id=38132268226`（須在來源 artifact 7 日保存期限內）。
3. 查看 prepare log：必須顯示 `RESUME_MODE=restore SOURCE_RUN=38132268226`；若顯示 `RESUME_MODE=fresh`，代表未提供恢復編號。
4. 查看 screen logs：`RESUME_TELEMETRY` 分別列出 `skipped_batches`、`reused_symbols`、`retried_symbols`、`new_symbols`、`written_batches`。目標為原有 39 檔重用、1 檔補查，實際結果以 log 為準。
5. 下載 audit artifact `fcn-pr17-coverage-audit`，包含 `coverage-summary.json` 與 `FCN_MORNING_RESEARCH_BRIEF.md`。
6. 完成恢復測試後，才能評估 full 範圍。Full 目前可能受到 Yahoo 限速、GitHub 90 分鐘 job 上限及 7 天 artifact 保存限制；**不要把 full 啟動等同完成全池資料**。

資料限制：尚未驗證證券類型、沒有資料再散布授權、沒有 HV/MDD/IV/財報/選擇權整合；不能發布至正式網站。
