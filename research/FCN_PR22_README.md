# PR #22｜自動斷點續跑與防呆

## 手動執行

GitHub Actions → FCN automated market-cap screening → Run workflow：

- **run_mode=auto_resume（預設）**：不必填 resume_run_id；自動選取同一 workflow 最新成功、且快照與 worker-0/worker-1 artifacts 尚未過期的執行。找不到來源即失敗停止，**不會偷偷 fresh**。
- **run_mode=manual_resume**：必須填入數字型 resume_run_id；來源必須是本 workflow 已成功執行，且快照與 worker artifacts 仍可用。否則停止。
- **run_mode=fresh**：明確重新建立股票池；resume_run_id 必須空白。
- **scope=pilot**：僅前兩個批次（40 檔）；**請先用 pilot 驗證**。
- **scope=full**：目前可能有 90 分鐘 job 時限、Yahoo 查詢限速、7 天 artifacts 過期等風險；不保證一次完成。不可直接當成正式行情晨訊。

## 驗收

1. prepare 應出現 `RESUME_MODE=restore SOURCE_RUN=<id>`。
2. screen worker-0 應出現 `SKIP_EXISTING 0`。
3. screen worker-1 應出現 `RESUME_TELEMETRY` 的 `retried_symbols=1`、`reused_symbols=19`（以實際上一輪 batch 狀態為準）。
4. audit 產出 `coverage-summary.json` 與 `FCN_MORNING_RESEARCH_BRIEF.md`。
5. 檢查 `new_symbols=0`（pilot 恢復同一快照時）。

## 邊界

- auto_resume 僅依可用 artifacts 與 workflow 成功狀態選來源，不會自動判斷 pilot/full 的歷史 scope；執行 full 前需人工審核。
- 研究資料尚未完成證券類型核驗、行情授權、HV/MDD/IV 模組；不可發布至正式網站。
- **本 PR 不會自行觸發 Actions，也不修改 index.html 或第 07/08 頁。**
