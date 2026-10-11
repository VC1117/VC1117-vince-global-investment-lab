# PR #16：完整股票池覆蓋規劃與品質稽核（研究用途）

本 PR **沒有完成 5,000+ 股票的市值查詢**。它解決先前 80 檔抽樣無法代表全市場的問題：為每次凍結的暫定股票池產生完整、不重疊、可稽核的 20 檔分批清單，並嚴格核對未處理、重複、錯誤快照、缺失市值狀態。

執行 GitHub Actions：`FCN full-universe coverage plan (manual, research only)`。工作流程會產生當次快照、全體批次規劃及 **remaining > 0、complete_universe_screen=false** 的初始報告，並測試稽核器。**不呼叫 Yahoo 市值 API**，不修改正式網站，不發佈行情。

要真正完成市值全篩選，後續必須將各批次結果按相同 snapshot_id 蒐集回來，補查失敗標的，並核實普通股證券種類。即使 complete_universe_screen=true，仍須授權來源與 security_type_verified=true 才可公開使用。嚴格門檻是 marketCap > 100,000,000,000 USD。
