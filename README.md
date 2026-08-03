# DOGEUSDT.P 相關係數網站

這個專案現在是：

- 基準：`DOGEUSDT.P`
- 比較對象：Bitget 其他 `USDT` 永續合約
- 比較週期：`1D` 天圖
- 比較視窗：最近 `20` 根日 K 收盤價
- 條件：相關係數 `0.70 ~ 1.00`
- 方向條件：只保留和 DOGEUSDT.P 最新日 K 同方向的標的
- 更新排程：每 `15` 分鐘重新抓一次資料

## 專案位置

`C:\Users\User\Documents\Codex專案\相關係數\TradingViewWebhookDashboard`

## ASP.NET 網站版

本地執行：

```powershell
cd "C:\Users\User\Documents\Codex專案\相關係數\TradingViewWebhookDashboard"
dotnet restore
dotnet run --launch-profile http
```

主要設定在 `appsettings.json` 的 `CorrelationDashboard` 區段。

## GitHub Pages 自動更新版

這個 repo 也支援像你之前那樣，直接靠 GitHub 自動更新靜態頁面：

- 工作流程：`.github/workflows/update-correlation-pages.yml`
- 更新腳本：`scripts/update_correlation_site.py`
- 輸出頁面：`docs/index.html`
- 輸出資料：`docs/correlation-data.json`
- 代號清單：`docs/hot_symbols.txt`

GitHub Pages 設定方式：

1. 到 repo 的 `Settings`
2. 打開 `Pages`
3. `Source` 選 `Deploy from a branch`
4. Branch 選 `main`
5. Folder 選 `/docs`

之後 GitHub Actions 會每 15 分鐘自動更新一次頁面，但內容是用最近 20 根日 K 計算相關係數。

## GitHub Actions

repo 內目前有一條 workflow：

- `.github/workflows/update-correlation-pages.yml`
  作用：每 15 分鐘更新 GitHub Pages 靜態頁面
