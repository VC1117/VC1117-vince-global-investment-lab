# PR #26｜證券類型核驗與替代市值來源評估

## 目的
承接 PR25 首批 24 檔精準診斷結果，**離線**整理 `missing_market_cap` / `invalid_market_cap` 股票的人工核驗佇列及替代市值來源評估準則。依已核實的 PR25 日誌，首批 24 檔有 20 檔缺少市值、4 檔可歸類為低於門檻；本 PR **不宣稱**已核驗 20 檔的證券身分。

## 使用
合併後，Actions → **FCN security type and alternate source review (offline)** → Run workflow，預設 `probe_run_id=38139109951`。工作流程驗證來源是成功完成的 PR25 run 且 artifact 未過期，離線執行測試與產出。

## 產出
- `FCN_SECURITY_REVIEW_QUEUE.csv`：20 檔人工待核驗清單，含交易所、上市狀態、證券類型、官方證據、替代市值來源、授權、簽核欄位；預設全部 unverified / pending_evidence。
- `FCN_SECURITY_SOURCE_REVIEW.json`：來源追溯與統計；security_type_verified、licensing_verified、alternative_source_approved 均 false。
- `FCN_SECURITY_SOURCE_REVIEW.md`：核驗順序、來源評估標準及合規關卡。

## 重要界線
**這是人工核驗準備工作，不是自動核實證券類型或替代來源的實際可用性。** 沒有進行外部查價、未取得商用資料授權、未更新 292 檔原失敗結果。後續若要自動查驗交易所名冊或替代行情 API，須先確認來源、合規條件、存取權限，再另立 PR。只新增四個檔案，不修改正式網站、Page07、Page08 或現有 FCN 篩選流程。
