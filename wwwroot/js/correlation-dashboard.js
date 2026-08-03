(function () {
  const initialDataNode = document.getElementById("initial-correlation-data");
  const resultsRoot = document.getElementById("correlation-results");
  const searchInput = document.getElementById("coin-search");
  const resultsSummary = document.getElementById("results-summary");
  const errorBanner = document.getElementById("error-banner");
  const lastUpdatedLabel = document.getElementById("last-updated-label");
  const lastSuccessLabel = document.getElementById("last-success-label");
  const scannedCountLabel = document.getElementById("scanned-count-label");
  const matchedCountLabel = document.getElementById("matched-count-label");
  const nextRefreshLabel = document.getElementById("next-refresh-label");
  const directionRuleLabel = document.getElementById("direction-rule");
  const btcDirectionPill = document.getElementById("btc-direction-pill");
  const btcChangeValue = document.getElementById("btc-change-value");
  const btcLastClose = document.getElementById("btc-last-close");
  const config = window.correlationDashboardConfig || {};

  if (!initialDataNode || !resultsRoot || !searchInput || !resultsSummary || !errorBanner || !lastUpdatedLabel || !lastSuccessLabel || !scannedCountLabel || !matchedCountLabel || !nextRefreshLabel || !directionRuleLabel || !btcDirectionPill || !btcChangeValue || !btcLastClose) {
    return;
  }

  const state = {
    snapshot: { results: [] },
    search: ""
  };

  try {
    state.snapshot = JSON.parse(initialDataNode.textContent || "{}");
  } catch (error) {
    console.error("Unable to parse initial correlation snapshot.", error);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll("\"", "&quot;")
      .replaceAll("'", "&#39;");
  }

  function getTrendClass(value) {
    if (value > 0) {
      return "up";
    }

    if (value < 0) {
      return "down";
    }

    return "flat";
  }

  function getFilteredResults() {
    const keyword = state.search.trim().toLowerCase();
    return (state.snapshot.results || []).filter((item) => {
      if (!keyword) {
        return true;
      }

      return String(item.symbol || "").toLowerCase().includes(keyword)
        || String(item.tradingViewSymbol || "").toLowerCase().includes(keyword);
    });
  }

  function renderSummary(filteredResults) {
    if (!filteredResults.length) {
      resultsSummary.textContent = "目前沒有符合搜尋條件的標的。";
      return;
    }

    resultsSummary.textContent = `顯示 ${filteredResults.length} / ${state.snapshot.matchedCount || 0} 個符合條件標的，全部掃描 ${state.snapshot.totalSymbolsScanned || 0} 個 USDT 永續合約。`;
  }

  function renderMeta() {
    lastUpdatedLabel.textContent = state.snapshot.updatedAtLocalText || "尚未更新";
    lastSuccessLabel.textContent = state.snapshot.lastSuccessfulRefreshLocalText || "尚未成功更新";
    scannedCountLabel.textContent = String(state.snapshot.totalSymbolsScanned || 0);
    matchedCountLabel.textContent = String(state.snapshot.matchedCount || 0);
    nextRefreshLabel.textContent = state.snapshot.nextScheduledRefreshLocalText || "-";
    directionRuleLabel.textContent = state.snapshot.directionRuleText || "";
    const baseTradingViewSymbol = state.snapshot.baseTradingViewSymbol || state.snapshot.baseSymbol || "DOGEUSDT.P";
    btcDirectionPill.textContent = state.snapshot.btcDirectionLabel || `等待 ${baseTradingViewSymbol} 最新日 K 方向`;
    btcDirectionPill.className = `direction-pill direction-pill--${escapeHtml(state.snapshot.btcDirection || "flat")}`;
    btcChangeValue.textContent = state.snapshot.basePriceChangeText || "0.00%";
    btcChangeValue.className = `spotlight-value metric-value is-${getTrendClass(Number(state.snapshot.basePriceChangePercent || 0))}`;
    btcLastClose.textContent = state.snapshot.baseLastCloseText || "-";

    if (state.snapshot.errorMessage) {
      errorBanner.hidden = false;
      errorBanner.textContent = `最新一次更新失敗: ${state.snapshot.errorMessage}`;
    } else {
      errorBanner.hidden = true;
      errorBanner.textContent = "";
    }
  }

  function renderResults(filteredResults) {
    if (!filteredResults.length) {
      resultsRoot.innerHTML = `
        <section class="empty-state">
          <strong>目前沒有可顯示的結果。</strong>
          <p class="mb-0">如果剛啟動網站，請等第一次背景更新完成；如果你有輸入搜尋條件，也可以先清空搜尋框再看看。</p>
        </section>
      `;
      return;
    }

    resultsRoot.innerHTML = filteredResults.map((item) => {
      const trendClass = getTrendClass(Number(item.priceChangePercent || 0));
      return `
        <article class="result-card">
          <div class="result-card-top">
            <div>
              <h3 class="result-symbol">${escapeHtml(item.symbol)}</h3>
              <div class="result-tradingview">${escapeHtml(item.tradingViewSymbol)}</div>
            </div>
            <span class="result-correlation">Corr ${escapeHtml(item.correlationText)}</span>
          </div>
          <div class="result-card-meta">
            <div class="metric">
              <span class="metric-label">日 K 變化</span>
              <span class="metric-value is-${trendClass}">${escapeHtml(item.priceChangeText)}</span>
            </div>
            <div class="metric">
              <span class="metric-label">最新收盤</span>
              <span class="metric-value">${escapeHtml(item.latestCloseText)}</span>
            </div>
            <span class="trend-badge trend-badge--${trendClass}">${escapeHtml(item.directionLabel)}</span>
          </div>
          <div class="result-card-actions">
            <small class="result-tradingview">TradingView 可直接貼上</small>
            <button class="copy-button" type="button" data-copy-symbol="${escapeHtml(item.tradingViewSymbol)}">複製代號</button>
          </div>
        </article>
      `;
    }).join("");
  }

  function render() {
    const filteredResults = getFilteredResults();
    renderMeta();
    renderSummary(filteredResults);
    renderResults(filteredResults);
  }

  async function refresh() {
    try {
      const response = await fetch(config.apiUrl || "/api/correlation-dashboard", { cache: "no-store" });
      if (!response.ok) {
        return;
      }

      state.snapshot = await response.json();
      render();
    } catch (error) {
      console.error("Correlation dashboard refresh failed.", error);
    }
  }

  async function copySymbol(symbol) {
    try {
      await navigator.clipboard.writeText(symbol);
      const buttons = document.querySelectorAll("[data-copy-symbol]");
      buttons.forEach((button) => {
        if (button.dataset.copySymbol !== symbol) {
          return;
        }

        const originalText = button.textContent;
        button.textContent = "已複製";
        window.setTimeout(() => {
          button.textContent = originalText;
        }, 1200);
      });
    } catch (error) {
      console.error("Copy symbol failed.", error);
      window.alert(`無法自動複製，請手動複製: ${symbol}`);
    }
  }

  searchInput.addEventListener("input", (event) => {
    state.search = event.target.value || "";
    render();
  });

  resultsRoot.addEventListener("click", (event) => {
    const button = event.target.closest("[data-copy-symbol]");
    if (!button) {
      return;
    }

    copySymbol(button.dataset.copySymbol || "");
  });

  render();
  refresh();
  window.setInterval(refresh, Number(config.pollMs || 60000));
})();
