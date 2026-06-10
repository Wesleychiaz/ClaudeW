#!/usr/bin/env python3
"""
StockPulse report generator.
Reads pre-fetched data JSON from stdin (or a file) and generates a self-contained HTML report.
Usage: python3 fetch_data.py NVDA | python3 generate_report.py
"""

import json
import sys
import os
import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(SCRIPT_DIR, "reports")


def rating_label(rec):
    mapping = {
        "strong_buy": ("STRONG BUY", "#4ade80"),
        "buy": ("BUY", "#86efac"),
        "hold": ("HOLD", "#fbbf24"),
        "sell": ("SELL", "#f87171"),
        "strong_sell": ("STRONG SELL", "#ef4444"),
    }
    return mapping.get((rec or "").lower(), (rec.upper() if rec else "N/A", "#888"))


def fg_color(score):
    if score == "N/A":
        return "#888"
    s = int(score)
    if s <= 25:   return "#ef4444"
    if s <= 45:   return "#f87171"
    if s <= 55:   return "#fbbf24"
    if s <= 75:   return "#86efac"
    return "#4ade80"


def perf_color(val):
    if val == "N/A" or val is None:
        return "#888"
    return "#4ade80" if float(val) >= 0 else "#f87171"


def fmt_pct(val, show_plus=True):
    if val == "N/A" or val is None:
        return "N/A"
    v = float(val)
    prefix = "+" if v >= 0 and show_plus else ""
    return f"{prefix}{v:.2f}%"


def fmt_price(val):
    if val == "N/A" or val is None:
        return "N/A"
    return f"${float(val):,.2f}"


def fmt_b(val):
    if val == "N/A" or val is None:
        return "N/A"
    return f"${float(val):.2f}B"


def build_report(data):
    meta = data["meta"]
    macro = data["macro"]
    s = data["stock"]
    perf = s.get("performance", {})
    fg = macro.get("fear_greed", {})
    rec_label, rec_color = rating_label(s.get("recommendation"))
    date_str = meta.get("generated_date", datetime.date.today().isoformat())
    stock_num = meta.get("report_number", "—")
    total_stocks = meta.get("total_stocks", "—")

    # Build news rows
    news_rows = ""
    for n in s.get("recent_news", [])[:5]:
        url = n.get("url", "")
        title = n.get("title", "")
        date = n.get("date", "")
        if url:
            news_rows += f'<li><span class="news-date">{date}</span><a href="{url}" target="_blank" rel="noopener" class="news-link">{title} ↗</a></li>'
        else:
            news_rows += f'<li><span class="news-date">{date}</span>{title}</li>'
    if not news_rows:
        news_rows = "<li>No recent headlines available</li>"

    # Performance rows
    perf_rows = ""
    for label, key in [("1 Day","1d"),("5 Days","5d"),("1 Month","1m"),("3 Months","3m"),("6 Months","6m"),("YTD","ytd"),("1 Year","1y")]:
        v = perf.get(key, "N/A")
        color = perf_color(v)
        perf_rows += f'<tr><td>{label}</td><td style="color:{color};font-weight:600">{fmt_pct(v)}</td></tr>'

    # 52w position bar
    lo = s.get("52w_low")
    hi = s.get("52w_high")
    price = s.get("price")
    bar_pct = 50
    if lo and hi and price and lo != "N/A" and hi != "N/A":
        try:
            bar_pct = round((float(price) - float(lo)) / (float(hi) - float(lo)) * 100)
            bar_pct = max(2, min(98, bar_pct))
        except Exception:
            bar_pct = 50

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>StockPulse — {s.get('ticker')} | {date_str}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:#0f0f0f;color:#fff;font-family:'Inter',system-ui,sans-serif;line-height:1.6;padding:0 0 60px}}
  a{{color:#f97316;text-decoration:none}}
  a:hover{{color:#fb923c}}
  .topbar{{background:#1a1a1a;border-bottom:1px solid #2a2a2a;padding:14px 32px;display:flex;align-items:center;justify-content:space-between}}
  .topbar-left{{display:flex;align-items:center;gap:16px}}
  .w-mark{{font-size:16px;font-weight:900;color:#fff;letter-spacing:-0.02em}}
  .w-mark span{{color:#f97316}}
  .back{{font-size:13px;color:#888}}
  .back:hover{{color:#fff}}
  .report-num{{font-size:12px;color:#555;border:1px solid #2a2a2a;border-radius:999px;padding:3px 10px}}
  .container{{max-width:860px;margin:0 auto;padding:40px 24px 0}}
  .header{{margin-bottom:32px}}
  .ticker-row{{display:flex;align-items:baseline;gap:12px;margin-bottom:8px;flex-wrap:wrap}}
  .ticker{{font-size:42px;font-weight:900;letter-spacing:-0.03em}}
  .company-name{{font-size:16px;color:#888}}
  .price-row{{display:flex;align-items:baseline;gap:10px;margin-bottom:4px}}
  .price{{font-size:32px;font-weight:700}}
  .day-change{{font-size:16px;font-weight:500}}
  .meta-row{{font-size:13px;color:#555;margin-top:4px}}
  .section{{margin-top:32px}}
  .section-title{{font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#888;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid #2a2a2a}}
  .grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
  .grid-3{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
  .card{{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;padding:18px}}
  .card-label{{font-size:11px;color:#888;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.08em}}
  .card-value{{font-size:22px;font-weight:700}}
  .card-sub{{font-size:12px;color:#555;margin-top:3px}}
  table{{width:100%;border-collapse:collapse}}
  td,th{{padding:9px 12px;font-size:13px;border-bottom:1px solid #2a2a2a;text-align:left}}
  th{{color:#888;font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:0.08em}}
  td:last-child,th:last-child{{text-align:right}}
  .macro-bar{{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;padding:20px 24px;display:flex;align-items:center;gap:32px;flex-wrap:wrap}}
  .macro-item{{display:flex;flex-direction:column;gap:4px}}
  .macro-label{{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.08em}}
  .macro-value{{font-size:20px;font-weight:700}}
  .macro-sub{{font-size:12px;color:#555}}
  .rec-badge{{display:inline-block;padding:4px 14px;border-radius:999px;font-size:12px;font-weight:700;letter-spacing:0.06em}}
  .range-bar{{background:#2a2a2a;border-radius:999px;height:6px;position:relative;margin:8px 0}}
  .range-fill{{background:#f97316;border-radius:999px;height:6px;position:absolute;left:0}}
  .range-labels{{display:flex;justify-content:space-between;font-size:11px;color:#555}}
  .news-list{{list-style:none;display:flex;flex-direction:column;gap:0}}
  .news-list li{{font-size:13px;color:#ccc;border-bottom:1px solid #222;padding:10px 0;line-height:1.5;display:flex;gap:16px;align-items:baseline}}
  .news-list li:last-child{{border-bottom:none}}
  .news-date{{font-size:11px;color:#555;flex-shrink:0;width:80px}}
  .news-link{{color:#ccc;text-decoration:none;transition:color 0.15s}}
  .news-link:hover{{color:#f97316}}
  .disclaimer{{margin-top:48px;padding:16px 20px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;font-size:12px;color:#555;line-height:1.6}}
  .tag{{display:inline-block;font-size:11px;border-radius:999px;padding:2px 10px;background:#1a1a1a;border:1px solid #2a2a2a;color:#888;margin-right:6px}}
  .analysis-section h3{{font-size:13px;font-weight:700;color:#f97316;text-transform:uppercase;letter-spacing:0.08em;margin:16px 0 8px}}
  .analysis-section p{{font-size:14px;color:#ccc;line-height:1.7;margin-bottom:12px}}
  .analysis-section ul{{list-style:none;display:flex;flex-direction:column;gap:6px;margin-bottom:12px}}
  .analysis-section ul li{{font-size:14px;color:#ccc;line-height:1.6;padding-left:14px;position:relative}}
  .analysis-section ul li::before{{content:"→";position:absolute;left:0;color:#f97316;font-size:12px}}
  .verdict-box{{background:#0f0f0f;border:1px solid #f97316;border-radius:8px;padding:16px 20px;margin-top:12px}}
  .verdict-label{{font-size:11px;color:#f97316;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px}}
  .verdict-text{{font-size:15px;font-weight:600;color:#fff}}
  .verdict-sub{{font-size:13px;color:#888;margin-top:4px}}
  @media(max-width:600px){{.grid-2,.grid-3{{grid-template-columns:1fr}}.ticker{{font-size:32px}}.price{{font-size:24px}}}}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-left">
    <span class="w-mark">W<span>.</span></span>
    <span style="font-size:13px;color:#555">StockPulse</span>
    <span class="report-num">Report {stock_num} of {total_stocks}</span>
  </div>
  <span style="font-size:12px;color:#555">{date_str}</span>
</div>

<div class="container">

  <div class="header">
    <div class="ticker-row">
      <span class="ticker">{s.get('ticker','')}</span>
      <span class="company-name">{s.get('name','')}</span>
    </div>
    <div class="price-row">
      <span class="price">{fmt_price(s.get('price'))}</span>
      <span class="day-change" style="color:{perf_color(s.get('day_change_pct'))}">{fmt_pct(s.get('day_change_pct'))} today</span>
    </div>
    <div class="meta-row">
      <span class="tag">{meta.get('watchlist_category','')}</span>
      <span class="tag">{meta.get('watchlist_subcategory') or meta.get('watchlist_sector','')}</span>
      <span class="tag">{s.get('sector','')}</span>
      &nbsp;{s.get('industry','')}
    </div>
  </div>

  <!-- MARKET SNAPSHOT -->
  <div class="section">
    <p class="section-title">Market Snapshot</p>
    <div class="macro-bar">
      <div class="macro-item">
        <span class="macro-label">Market Cap</span>
        <span class="macro-value">{fmt_b(s.get('market_cap_b'))}</span>
        <span class="macro-sub">USD</span>
      </div>
      <div class="macro-item">
        <span class="macro-label">Beta</span>
        <span class="macro-value">{s.get('beta','N/A')}</span>
        <span class="macro-sub">vs S&P 500</span>
      </div>
      <div class="macro-item">
        <span class="macro-label">Analyst Consensus</span>
        <span class="rec-badge" style="background:{rec_color}22;color:{rec_color};border:1px solid {rec_color}44">{rec_label}</span>
        <span class="macro-sub">{s.get('analyst_count','N/A')} analysts</span>
      </div>
    </div>
  </div>

  <!-- PRICE PERFORMANCE -->
  <div class="section">
    <p class="section-title">Price Performance</p>
    <div class="grid-2">
      <div class="card">
        <table>
          <thead><tr><th>Period</th><th>Return</th></tr></thead>
          <tbody>{perf_rows}</tbody>
        </table>
      </div>
      <div class="card">
        <p class="card-label">52-Week Range</p>
        <div style="margin-top:8px">
          <div class="range-bar"><div class="range-fill" style="width:{bar_pct}%"></div></div>
          <div class="range-labels"><span>{fmt_price(s.get('52w_low'))}</span><span style="color:#f97316">{fmt_price(s.get('price'))}</span><span>{fmt_price(s.get('52w_high'))}</span></div>
        </div>
        <div style="margin-top:24px">
          <p class="card-label">Analyst Price Target</p>
          <p style="font-size:22px;font-weight:600;margin-top:4px">{fmt_price(s.get('target_mean_price'))}</p>
          <p style="font-size:12px;color:#555;margin-top:4px">Range: {fmt_price(s.get('target_low_price'))} — {fmt_price(s.get('target_high_price'))}</p>
        </div>
        <div style="margin-top:24px">
          <p class="card-label">Avg Daily Volume</p>
          <p style="font-size:18px;font-weight:600;margin-top:4px">{s.get('avg_volume_m','N/A')}M shares</p>
        </div>
      </div>
    </div>
  </div>

  <!-- FINANCIALS -->
  <div class="section">
    <p class="section-title">Financials (TTM)</p>
    <div class="grid-3">
      <div class="card">
        <p class="card-label">Revenue</p>
        <p class="card-value">{fmt_b(s.get('revenue_ttm_b'))}</p>
        <p class="card-sub" style="color:{perf_color(s.get('revenue_growth_yoy_pct'))}">YoY {fmt_pct(s.get('revenue_growth_yoy_pct'))}</p>
      </div>
      <div class="card">
        <p class="card-label">Free Cash Flow</p>
        <p class="card-value">{fmt_b(s.get('free_cash_flow_b'))}</p>
        <p class="card-sub">Cash: {fmt_b(s.get('cash_b'))}</p>
      </div>
      <div class="card">
        <p class="card-label">Earnings Growth</p>
        <p class="card-value" style="color:{perf_color(s.get('earnings_growth_yoy_pct'))}">{fmt_pct(s.get('earnings_growth_yoy_pct'))}</p>
        <p class="card-sub">YoY</p>
      </div>
    </div>
    <div class="grid-3" style="margin-top:12px">
      <div class="card">
        <p class="card-label">Gross Margin</p>
        <p class="card-value">{fmt_pct(s.get('gross_margin_pct'),False)}</p>
      </div>
      <div class="card">
        <p class="card-label">Operating Margin</p>
        <p class="card-value">{fmt_pct(s.get('operating_margin_pct'),False)}</p>
      </div>
      <div class="card">
        <p class="card-label">Net Margin</p>
        <p class="card-value">{fmt_pct(s.get('net_margin_pct'),False)}</p>
      </div>
    </div>
  </div>

  <!-- VALUATION -->
  <div class="section">
    <p class="section-title">Valuation</p>
    <div class="grid-3">
      <div class="card">
        <p class="card-label">P/E (TTM)</p>
        <p class="card-value">{s.get('pe_ttm','N/A')}x</p>
      </div>
      <div class="card">
        <p class="card-label">Forward P/E</p>
        <p class="card-value">{s.get('forward_pe','N/A')}x</p>
      </div>
      <div class="card">
        <p class="card-label">P/S Ratio</p>
        <p class="card-value">{s.get('ps_ratio','N/A')}x</p>
      </div>
      <div class="card">
        <p class="card-label">P/B Ratio</p>
        <p class="card-value">{s.get('pb_ratio','N/A')}x</p>
      </div>
      <div class="card">
        <p class="card-label">Total Debt</p>
        <p class="card-value">{fmt_b(s.get('debt_b'))}</p>
      </div>
      <div class="card">
        <p class="card-label">Cash on Hand</p>
        <p class="card-value">{fmt_b(s.get('cash_b'))}</p>
      </div>
    </div>
  </div>

  <!-- ANALYSIS SECTION -->
  <div class="section" id="analysis">
    <p class="section-title">AI Analysis</p>
    <div class="card analysis-section" style="padding:24px" id="analysis-content">
      <p id="analysis-text" style="color:#888;font-style:italic;font-size:14px">Analysis will be generated by Claude Code when the report runs.</p>
    </div>
  </div>

  <!-- NEWS -->
  <div class="section">
    <p class="section-title">Recent Headlines</p>
    <div class="card" style="padding:20px 24px">
      <ul class="news-list">{news_rows}</ul>
    </div>
  </div>

  <div class="disclaimer">
    <strong>Disclaimer:</strong> This report is generated automatically for personal research purposes only.
    It does not constitute financial advice. Past performance is not indicative of future results.
    Always do your own due diligence before making investment decisions.
    Data sourced from Yahoo Finance and public APIs. Generated {meta.get('generated_time_sgt','')}.
  </div>

</div>
</body>
</html>"""
    return html


def main():
    raw = sys.stdin.read()
    data = json.loads(raw)

    ticker = data["meta"]["ticker"]
    date_str = data["meta"]["generated_date"]

    report_html = build_report(data)

    filename = f"{date_str}-{ticker}.html"
    filepath = os.path.join(REPORTS_DIR, filename)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(filepath, "w") as f:
        f.write(report_html)

    print(f"Report saved: {filepath}")
    return filepath, data


if __name__ == "__main__":
    main()
