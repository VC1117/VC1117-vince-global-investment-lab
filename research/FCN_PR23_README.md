# PR #23｜完整股票池專用執行入口

## 一鍵啟動

GitHub → Actions → **FCN FULL universe screening (one-click research)** → **Run workflow** → Branch: main → Run workflow。

此入口**沒有 scope 下拉選單**，固定透過 GitHub Actions API 啟動既有 `fcn-automated-cap-screen.yml`，傳入：
- `run_mode=auto_resume`
- `scope=full`
- `resume_run_id=""`
- `ref=main`

## 重要：兩筆工作流程

入口 `FCN FULL universe screening` 成功只代表**派送請求成功**，不代表篩選完成。真正執行與稽核在另一筆 `FCN automated market-cap screening (manual research)`，必須檢查：

1. prepare: `MODE full PLANNED_SHARDS 262 WORKERS 12`（目前快照為 262 個批次）。
2. prepare: `RESUME_MODE=restore SOURCE_RUN=<id> SCOPE=full`。
3. screen: 12 個分組的執行結果；注意 API 限速、90 分鐘時限與失敗數。
4. audit: `coverage-summary.json`，確認 `processed_unique`、`remaining`、`failed`、`audit_errors`。
5. `complete_universe_screen=true` 且 `failed=0` 才表示目前凍結的候選股票篩選完整；**證券類型核驗及資料授權仍另外進行**。

若 `auto_resume` 找不到尚未過期的 artifacts，主工作流程會停止，不會自動重新建池。Artifacts 保留 7 天。請勿在完整篩選期間並行啟動多次，以免查詢限速或結果競爭。

本 PR 只新增獨立 workflow 與操作說明，不修改原本 pilot/full 邏輯、首頁、Page07 或 Page08，也不自行執行 full 查詢。
