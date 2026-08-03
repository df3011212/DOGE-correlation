import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
DATA_PATH = DOCS_DIR / "correlation-data.json"
HTML_PATH = DOCS_DIR / "index.html"
TEXT_PATH = DOCS_DIR / "hot_symbols.txt"
NOJEKYLL_PATH = DOCS_DIR / ".nojekyll"

BASE_SYMBOL = "DOGEUSDT"
BASE_TRADINGVIEW_SYMBOL = "DOGEUSDT.P"
PRODUCT_TYPE = "usdt-futures"
GRANULARITY = "1D"
CANDLE_LIMIT = 20
MIN_CORRELATION = 0.70
MAX_CORRELATION = 1.00
TOP_RESULT_COUNT = 120
TIMEZONE_OFFSET = timezone(timedelta(hours=8))


def get_contract_symbols(session: requests.Session) -> list[str]:
    response = session.get(
        "https://api.bitget.com/api/v2/mix/market/contracts",
        params={"productType": PRODUCT_TYPE},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "00000":
        raise RuntimeError(f"Unable to load contracts: {payload.get('msg')}")

    symbols: list[str] = []
    for item in payload.get("data", []):
        symbol = str(item.get("symbol", "")).upper()
        if (
            item.get("symbolType") == "perpetual"
            and item.get("symbolStatus") == "normal"
            and str(item.get("quoteCoin", "")).upper() == "USDT"
            and symbol.endswith("USDT")
            and symbol.isascii()
            and symbol.replace("USDT", "").isalnum()
        ):
            symbols.append(symbol)

    return sorted(set(symbols))


def get_close_series(session: requests.Session, symbol: str) -> list[float]:
    response = session.get(
        "https://api.bitget.com/api/v2/mix/market/candles",
        params={
            "symbol": symbol,
            "productType": PRODUCT_TYPE,
            "granularity": GRANULARITY,
            "limit": CANDLE_LIMIT,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "00000":
        raise RuntimeError(f"Unable to load candles for {symbol}: {payload.get('msg')}")

    rows = payload.get("data", [])
    series = []
    for row in rows:
        if len(row) < 5:
            continue
        series.append((int(row[0]), float(row[4])))

    series.sort(key=lambda item: item[0])
    return [close for _, close in series][-CANDLE_LIMIT:]


def pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return float("nan")

    count = len(left)
    sum_left = sum(left)
    sum_right = sum(right)
    sum_left_sq = sum(value * value for value in left)
    sum_right_sq = sum(value * value for value in right)
    sum_product = sum(a * b for a, b in zip(left, right))

    numerator = (count * sum_product) - (sum_left * sum_right)
    denominator_left = (count * sum_left_sq) - (sum_left * sum_left)
    denominator_right = (count * sum_right_sq) - (sum_right * sum_right)
    if denominator_left <= 0 or denominator_right <= 0:
        return float("nan")

    return numerator / math.sqrt(denominator_left * denominator_right)


def price_change_percent(series: list[float]) -> float:
    if len(series) < 2 or series[-2] == 0:
        return 0.0
    return ((series[-1] - series[-2]) / series[-2]) * 100.0


def trend_key(change_percent: float) -> str:
    if change_percent > 0:
        return "up"
    if change_percent < 0:
        return "down"
    return "flat"


def format_percent(value: float) -> str:
    if value > 0:
        return f"+{value:.2f}%"
    if value < 0:
        return f"{value:.2f}%"
    return "0.00%"


def format_price(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")


def build_payload() -> dict:
    session = requests.Session()
    session.headers.update({"User-Agent": "DOGE-correlation-dashboard/1.0"})

    symbols = get_contract_symbols(session)
    if BASE_SYMBOL not in symbols:
        raise RuntimeError(f"Missing base symbol {BASE_SYMBOL}")

    base_series = get_close_series(session, BASE_SYMBOL)
    if len(base_series) < CANDLE_LIMIT:
        raise RuntimeError(f"{BASE_TRADINGVIEW_SYMBOL} candle count is insufficient.")

    base_change = price_change_percent(base_series)
    btc_direction = trend_key(base_change)

    if btc_direction == "up":
        direction_label = f"{BASE_TRADINGVIEW_SYMBOL} 最新日 K 上漲"
        direction_rule = f"只保留和 {BASE_TRADINGVIEW_SYMBOL} 最新日 K 同方向上漲，且相關係數介於 {MIN_CORRELATION:.2f} 到 {MAX_CORRELATION:.2f} 的標的。"
    elif btc_direction == "down":
        direction_label = f"{BASE_TRADINGVIEW_SYMBOL} 最新日 K 下跌"
        direction_rule = f"目前 {BASE_TRADINGVIEW_SYMBOL} 在下跌，因此列表改為保留和 {BASE_TRADINGVIEW_SYMBOL} 最新日 K 同方向下跌，且相關係數介於 {MIN_CORRELATION:.2f} 到 {MAX_CORRELATION:.2f} 的標的。"
    else:
        direction_label = f"{BASE_TRADINGVIEW_SYMBOL} 最新日 K 持平"
        direction_rule = f"{BASE_TRADINGVIEW_SYMBOL} 最新日 K 幾乎持平，因此本次以相關係數 {MIN_CORRELATION:.2f} 到 {MAX_CORRELATION:.2f} 為主，不額外限制方向。"

    results = []
    for symbol in symbols:
        if symbol == BASE_SYMBOL:
            continue

        try:
            series = get_close_series(session, symbol)
        except Exception:
            continue

        if len(series) != len(base_series):
            continue

        corr = pearson(base_series, series)
        if math.isnan(corr) or corr < MIN_CORRELATION or corr > MAX_CORRELATION:
            continue

        change = price_change_percent(series)
        if btc_direction != "flat" and trend_key(change) != btc_direction:
            continue

        results.append(
            {
                "symbol": symbol,
                "tradingViewSymbol": f"{symbol}.P",
                "correlation": round(corr, 4),
                "correlationText": f"{corr:.4f}",
                "priceChangePercent": round(change, 4),
                "priceChangeText": format_percent(change),
                "latestClose": series[-1],
                "latestCloseText": format_price(series[-1]),
                "directionLabel": "同方向",
                "trend": trend_key(change),
            }
        )

    results.sort(
        key=lambda item: (
            -item["correlation"],
            -abs(item["priceChangePercent"]),
            item["symbol"],
        )
    )
    results = results[:TOP_RESULT_COUNT]

    now = datetime.now(TIMEZONE_OFFSET)
    next_run = now + timedelta(minutes=15)

    return {
        "title": f"{BASE_TRADINGVIEW_SYMBOL} 相關係數 ({MIN_CORRELATION:.1f}~{MAX_CORRELATION:.1f}) 日 K",
        "baseTradingViewSymbol": BASE_TRADINGVIEW_SYMBOL,
        "windowLabel": f"{GRANULARITY} x {CANDLE_LIMIT} 根 K 線",
        "correlationRangeLabel": f"{MIN_CORRELATION:.2f} ~ {MAX_CORRELATION:.2f}",
        "marketLabel": "Bitget USDT 永續合約",
        "updatedAtLocalText": now.strftime("%Y-%m-%d %H:%M:%S"),
        "nextScheduledRefreshLocalText": next_run.strftime("%Y-%m-%d %H:%M:%S"),
        "refreshIntervalMinutes": 15,
        "btcDirection": btc_direction,
        "btcDirectionLabel": direction_label,
        "basePriceChangePercent": round(base_change, 4),
        "basePriceChangeText": format_percent(base_change),
        "baseLastCloseText": format_price(base_series[-1]),
        "totalSymbolsScanned": max(len(symbols) - 1, 0),
        "matchedCount": len(results),
        "directionRuleText": direction_rule,
        "results": results,
    }


def render_html(data: dict) -> str:
    cards = []
    for item in data["results"]:
        cards.append(
            f"""
            <article class="result-card">
              <div class="result-top">
                <div>
                  <h3>{item['symbol']}</h3>
                  <div class="sub">{item['tradingViewSymbol']}</div>
                </div>
                <span class="corr">Corr {item['correlationText']}</span>
              </div>
              <div class="metrics">
                <div class="metric">
                  <span class="label">日 K 變化</span>
                  <strong class="trend-{item['trend']}">{item['priceChangeText']}</strong>
                </div>
                <div class="metric">
                  <span class="label">最新收盤</span>
                  <strong>{item['latestCloseText']}</strong>
                </div>
                <div class="metric">
                  <span class="label">方向</span>
                  <strong>{item['directionLabel']}</strong>
                </div>
              </div>
            </article>
            """
        )

    cards_html = "\n".join(cards) if cards else """
        <section class="empty-state">
          目前沒有符合條件的標的，請等下一輪更新。
        </section>
    """

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{data['title']}</title>
  <style>
    :root {{
      --bg: #f4f1ea;
      --panel: rgba(255, 251, 245, 0.9);
      --ink: #1f2933;
      --muted: #5e6b75;
      --line: rgba(55, 40, 18, 0.12);
      --accent: #b45309;
      --positive: #166534;
      --negative: #b42318;
      --shadow: 0 26px 60px rgba(72, 48, 21, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Segoe UI", "Microsoft JhengHei", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(255, 205, 124, 0.52), transparent 28%),
        radial-gradient(circle at top right, rgba(255, 244, 213, 0.72), transparent 30%),
        linear-gradient(180deg, #fffaf1 0%, #f3eee3 52%, #ebe4d8 100%);
    }}
    .shell {{ width: min(1200px, calc(100% - 24px)); margin: 0 auto; padding: 24px 0 40px; }}
    .hero, .strip > div, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.3fr .8fr;
      gap: 18px;
      padding: 24px;
      margin-bottom: 18px;
    }}
    .eyebrow {{
      margin: 0 0 8px;
      color: var(--accent);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: .16em;
      text-transform: uppercase;
    }}
    h1 {{ margin: 0; font-size: clamp(32px, 4vw, 54px); line-height: .95; }}
    p {{ line-height: 1.7; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }}
    .chip {{
      padding: 9px 14px;
      border-radius: 999px;
      background: rgba(255, 245, 231, 0.9);
      color: #8c5100;
      font-size: 14px;
      font-weight: 700;
    }}
    .spotlight {{
      padding: 20px;
      border-radius: 20px;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255,248,238,.96), rgba(252,244,232,.92));
    }}
    .spotlight .dir {{ font-size: 14px; font-weight: 800; }}
    .spotlight .price {{ font-size: 42px; font-weight: 800; margin: 8px 0; }}
    .trend-up {{ color: var(--positive); }}
    .trend-down {{ color: var(--negative); }}
    .trend-flat {{ color: #475467; }}
    .strip {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}
    .strip > div {{ padding: 18px; }}
    .strip .label {{
      display: block;
      margin-bottom: 6px;
      color: var(--muted);
      font-size: 12px;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    .panel {{ padding: 22px; }}
    .panel-head {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-end;
      margin-bottom: 16px;
    }}
    .summary {{ color: var(--muted); margin-bottom: 16px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
      gap: 14px;
    }}
    .result-card {{
      background: rgba(255,255,255,.82);
      border: 1px solid rgba(55, 40, 18, 0.09);
      border-radius: 20px;
      padding: 16px;
    }}
    .result-top, .metrics {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
    }}
    .result-top h3 {{ margin: 0; font-size: 28px; }}
    .sub, .label {{ color: var(--muted); }}
    .corr {{
      background: rgba(31,41,51,.06);
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 800;
    }}
    .metric {{
      display: grid;
      gap: 4px;
    }}
    .label {{
      font-size: 12px;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    .empty-state {{
      padding: 18px;
      border: 1px dashed rgba(180, 83, 9, 0.28);
      border-radius: 18px;
      color: var(--muted);
    }}
    a.download {{
      color: inherit;
      font-weight: 700;
    }}
    @media (max-width: 900px) {{
      .hero, .strip {{ grid-template-columns: 1fr; }}
      .panel-head, .result-top, .metrics {{ flex-direction: column; align-items: flex-start; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div>
        <p class="eyebrow">GitHub Pages Auto Update</p>
        <h1>{data['title']}</h1>
        <p>
          GitHub Actions 每 15 分鐘自動更新一次，但相關係數是用 Bitget USDT 永續合約的
          {data['windowLabel']} 收盤價，計算 {data['baseTradingViewSymbol']} 與其他標的的日線同步程度，
          並保留相關係數介於 {data['correlationRangeLabel']}、且和 {data['baseTradingViewSymbol']} 最新日 K 方向一致的標的。
        </p>
        <div class="chips">
          <span class="chip">{data['windowLabel']}</span>
          <span class="chip">相關係數 {data['correlationRangeLabel']}</span>
          <span class="chip">資料源 {data['marketLabel']}</span>
        </div>
      </div>
      <div class="spotlight">
        <div class="dir trend-{data['btcDirection']}">{data['btcDirectionLabel']}</div>
        <div class="price trend-{data['btcDirection']}">{data['basePriceChangeText']}</div>
        <div>{data['baseTradingViewSymbol']} 最新價格 <strong>{data['baseLastCloseText']}</strong></div>
        <div style="margin-top: 10px; color: var(--muted);">下次排程 {data['nextScheduledRefreshLocalText']}</div>
      </div>
    </section>

    <section class="strip">
      <div><span class="label">最後更新</span><strong>{data['updatedAtLocalText']}</strong></div>
      <div><span class="label">掃描合約數</span><strong>{data['totalSymbolsScanned']}</strong></div>
      <div><span class="label">符合條件數</span><strong>{data['matchedCount']}</strong></div>
      <div><span class="label">TXT 清單</span><a class="download" href="hot_symbols.txt">下載代號</a></div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Filter Rule</p>
          <h2 style="margin:0;">篩選結果</h2>
        </div>
        <div class="summary">{data['directionRuleText']}</div>
      </div>
      <div class="grid">
        {cards_html}
      </div>
    </section>
  </div>
</body>
</html>
"""


def write_outputs(data: dict) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    HTML_PATH.write_text(render_html(data), encoding="utf-8")
    NOJEKYLL_PATH.write_text("", encoding="utf-8")

    if data["results"]:
        lines = [item["tradingViewSymbol"] for item in data["results"]]
        TEXT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        TEXT_PATH.write_text("目前沒有符合條件的標的\n", encoding="utf-8")


def main() -> None:
    data = build_payload()
    write_outputs(data)
    print(f"Updated {HTML_PATH}")


if __name__ == "__main__":
    main()
