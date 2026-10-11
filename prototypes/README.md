# FCN 第 08 頁獨立預覽（PR #14）

- 開啟 `prototypes/fcn-page08-preview.html` 可在瀏覽器離線操作。
- **不修改 index.html，不會加入正式網站導覽**；僅供介面驗收。
- 搜尋、產業篩選、HV/MDD/90日報酬排序、最多四檔 HV20 比較、缺值顯示。
- 所有 `DEMO-*` 代碼及百分比為**虛構模擬資料**，不可用於客戶投資建議。
- 正式資料契約欄位：`symbol`, `name`, `sector`, `marketCapBn`, `lastTradeDate`, `hv20`, `hv30`, `hv60`, `hv90`, `hv180`, `hv252`, `mdd20`, `mdd90`, `ret90`, `iv30`。缺值為 `null`。
- 正式上線前需：完整證券類型驗證、全部千億美元市值篩選、授權數據、日線檢核與更新日期、IV30 獨立來源。
