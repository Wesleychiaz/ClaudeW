#!/usr/bin/env python3
"""Scans reports/ and rebuilds stockpulse/index.html"""

import os
import json
import re
import datetime
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(SCRIPT_DIR, "reports")
WATCHLIST_PATH = os.path.join(SCRIPT_DIR, "watchlist.json")

# 2026 announcement calendars (update in Jan 2027)
FOMC_2026 = [
    datetime.date(2026, 1, 28), datetime.date(2026, 3, 18),
    datetime.date(2026, 4, 29), datetime.date(2026, 6, 17),
    datetime.date(2026, 7, 29), datetime.date(2026, 9, 16),
    datetime.date(2026, 10, 28), datetime.date(2026, 12, 9),
]
CPI_2026 = [
    datetime.date(2026, 1, 14), datetime.date(2026, 2, 11),
    datetime.date(2026, 3, 11), datetime.date(2026, 4, 10),
    datetime.date(2026, 5, 12), datetime.date(2026, 6, 10),
    datetime.date(2026, 7, 14), datetime.date(2026, 8, 12),
    datetime.date(2026, 9, 11), datetime.date(2026, 10, 14),
    datetime.date(2026, 11, 10), datetime.date(2026, 12, 10),
]
NFP_2026 = [
    datetime.date(2026, 1, 9),  datetime.date(2026, 2, 6),
    datetime.date(2026, 3, 6),  datetime.date(2026, 4, 3),
    datetime.date(2026, 5, 8),  datetime.date(2026, 6, 5),
    datetime.date(2026, 7, 2),  datetime.date(2026, 8, 7),
    datetime.date(2026, 9, 4),  datetime.date(2026, 10, 2),
    datetime.date(2026, 11, 6), datetime.date(2026, 12, 4),
]

# Fallback values when FRED is unreachable — update when data changes
FALLBACK = {
    "fed_rate": "3.75%",          # DFEDTARU as of 2026-06-09
    "cpi_yoy": "4.2%",            # May 2026 YoY, released 2026-06-10
    "nfp_change": "+172K",        # May 2026 (159,001K - 158,829K), released 2026-06-05
}


def next_date(dates):
    today = datetime.date.today()
    future = [d for d in dates if d > today]
    return future[0].strftime("%-d %b") if future else "—"


def next_nfp():
    return next_date(NFP_2026)


def get_fred_csv(series_id):
    """Fetch FRED public CSV. Works around LibreSSL issues on macOS."""
    import ssl, urllib.request
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
            text = resp.read().decode("utf-8")
        lines = [l for l in text.strip().split("\n") if l and not l.startswith("DATE")]
        return lines
    except Exception:
        return []


def get_fred_value(series_id):
    lines = get_fred_csv(series_id)
    if lines:
        last = lines[-1].split(",")
        return last[1].strip() if len(last) > 1 else None
    return None


def get_fear_greed():
    """Fetch CNN Fear & Greed Index (stock market sentiment, 0-100).
    No fallback to alternative.me — that measures crypto, not stocks."""
    endpoints = [
        "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
        "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/",
    ]
    for url in endpoints:
        try:
            r = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://edition.cnn.com/markets/fear-and-greed",
                "Accept": "application/json",
            }, timeout=12)
            if r.status_code == 200 and r.text.strip():
                data = r.json()
                fg = data.get("fear_and_greed", {})
                score = round(fg.get("score", 0))
                rating = fg.get("rating", "").replace("_", " ").title()
                if score > 0:
                    return score, rating
        except Exception:
            pass
    return "—", "—"


def fg_color(score):
    if score == "—":
        return "#888"
    s = int(score)
    if s <= 25: return "#ef4444"
    if s <= 45: return "#f87171"
    if s <= 55: return "#fbbf24"
    if s <= 75: return "#86efac"
    return "#4ade80"


def get_macro_data():
    fg_score, fg_rating = get_fear_greed()

    fed_raw = get_fred_value("DFEDTARU")  # Upper bound of Fed Funds target rate
    fed_rate = f"{float(fed_raw):.2f}%" if fed_raw else FALLBACK["fed_rate"]

    cpi_raw = get_fred_value("CPIAUCSL")
    cpi_prev = get_fred_value("CPIAUCSL")
    # Calculate YoY — fetch last 13 months via CSV
    cpi_yoy = FALLBACK["cpi_yoy"]
    try:
        lines = get_fred_csv("CPIAUCSL")
        if len(lines) >= 13:
            latest = float(lines[-1].split(",")[1])
            year_ago = float(lines[-13].split(",")[1])
            cpi_yoy = f"{((latest / year_ago) - 1) * 100:.1f}%"
    except Exception:
        pass

    nfp_change = FALLBACK["nfp_change"]
    try:
        lines = get_fred_csv("PAYEMS")
        if len(lines) >= 2:
            latest = float(lines[-1].split(",")[1])
            prev = float(lines[-2].split(",")[1])
            diff = round((latest - prev) * 1000)  # PAYEMS in thousands
            sign = "+" if diff >= 0 else ""
            nfp_change = f"{sign}{diff:,}K"
    except Exception:
        pass

    return {
        "fg_score": fg_score, "fg_rating": fg_rating,
        "fed_rate": fed_rate, "fed_next": next_date(FOMC_2026),
        "cpi_yoy": cpi_yoy, "cpi_next": next_date(CPI_2026),
        "nfp_change": nfp_change, "nfp_next": next_nfp(),
    }

def get_watchlist_progress():
    try:
        with open(WATCHLIST_PATH) as f:
            wl = json.load(f)
        idx = wl["current_index"]
        total = len(wl["stocks"])
        next_stock = wl["stocks"][idx]
        return idx, total, next_stock
    except Exception:
        return 0, 25, {}

def get_reports():
    if not os.path.exists(REPORTS_DIR):
        return []
    files = [f for f in os.listdir(REPORTS_DIR) if f.endswith(".html")]
    reports = []
    pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})-([A-Z]+)\.html$")
    for f in files:
        m = pattern.match(f)
        if m:
            mtime = os.path.getmtime(os.path.join(REPORTS_DIR, f))
            reports.append({"date": m.group(1), "ticker": m.group(2), "filename": f, "mtime": mtime})
    reports.sort(key=lambda x: (x["date"], x["mtime"]), reverse=True)
    return reports

def build_index():
    reports = get_reports()
    idx, total, next_stock = get_watchlist_progress()
    completed = idx
    today = datetime.date.today().isoformat()
    macro = get_macro_data()

    # Report cards HTML
    if reports:
        latest = reports[0]
        latest_card = f"""
        <a href="reports/{latest['filename']}" class="latest-card">
          <div class="latest-label">Latest Report — {latest['date']}</div>
          <div class="latest-ticker">{latest['ticker']}</div>
          <div class="latest-sub">Click to read full analysis →</div>
        </a>"""
    else:
        latest_card = '<div class="latest-card"><div class="latest-label">No reports yet</div><div class="latest-ticker">—</div><div class="latest-sub">Run ./run_today.sh to generate your first report</div></div>'

    archive_rows = ""
    for r in reports[1:]:
        archive_rows += f'<a href="reports/{r["filename"]}" class="archive-row"><span class="ar-date">{r["date"]}</span><span class="ar-ticker">{r["ticker"]}</span><span class="ar-arrow">→</span></a>'
    if not archive_rows:
        archive_rows = '<div style="color:#444;font-size:13px;padding:16px 0">Archive will build up as daily reports are generated.</div>'

    # Watchlist progress
    watchlist_items = ""
    try:
        with open(WATCHLIST_PATH) as f:
            wl = json.load(f)
        covered = set(r["ticker"] for r in reports)
        for i, stock in enumerate(wl["stocks"]):
            is_done = stock["ticker"] in covered
            is_next = i == idx
            cls = "wl-done" if is_done else ("wl-next" if is_next else "wl-pending")
            label = "✓" if is_done else ("→" if is_next else str(i+1))
            subcat = stock.get("subcategory", stock.get("sector", ""))
            watchlist_items += f'<div class="wl-item {cls}"><span class="wl-num">{label}</span><span class="wl-ticker">{stock["ticker"]}</span><span class="wl-name">{stock["name"]}</span><span class="wl-subcat">{subcat}</span><span class="wl-cat">{stock["category"]}</span></div>'
    except Exception:
        watchlist_items = '<div style="color:#444">Watchlist not available</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>StockPulse — Daily AI Stock Analysis</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:#0f0f0f;color:#e8e8e8;font-family:'Inter',system-ui,sans-serif;line-height:1.6}}
  a{{color:inherit;text-decoration:none}}
  .topbar{{background:#161616;border-bottom:1px solid #2a2a2a;padding:14px 32px;display:flex;align-items:center;justify-content:space-between}}
  .w-mark{{font-size:16px;font-weight:900;color:#fff;letter-spacing:-0.02em;margin-right:12px}}
  .w-mark span{{color:#f97316}}
  .back{{font-size:13px;color:#aaa}}
  .back:hover{{color:#fff}}
  .container{{max-width:860px;margin:0 auto;padding:48px 24px 80px}}
  .hero{{margin-bottom:8px}}
  .hero h1{{font-size:36px;font-weight:900;letter-spacing:-0.03em;margin-bottom:8px;color:#fff}}
  .hero p{{font-size:15px;color:#aaa;margin-bottom:4px}}
  .stats-bar{{display:flex;gap:16px;margin:28px 0;flex-wrap:wrap}}
  .stat{{background:#1e1e1e;border:1px solid #2a2a2a;border-radius:8px;padding:14px 22px;display:flex;flex-direction:column;gap:3px}}
  .stat-label{{font-size:11px;color:#aaa;text-transform:uppercase;letter-spacing:0.08em}}
  .stat-value{{font-size:22px;font-weight:700;color:#fff}}
  .latest-card{{display:block;background:#1e1e1e;border:1px solid #2a2a2a;border-radius:8px;padding:28px 32px;margin-bottom:32px;transition:border-color 0.2s,background 0.2s}}
  .latest-card:hover{{border-color:#f97316;background:#222}}
  .latest-label{{font-size:11px;color:#aaa;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px}}
  .latest-ticker{{font-size:48px;font-weight:900;letter-spacing:-0.03em;margin-bottom:4px;color:#fff}}
  .latest-sub{{font-size:14px;color:#f97316}}
  .section-title{{font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#aaa;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid #2a2a2a}}
  .archive{{margin-bottom:40px}}
  .archive-row{{display:flex;align-items:center;gap:16px;padding:12px 0;border-bottom:1px solid #222;transition:color 0.15s}}
  .archive-row:hover{{color:#f97316}}
  .ar-date{{font-size:12px;color:#666;width:100px;flex-shrink:0}}
  .ar-ticker{{font-size:15px;font-weight:600;flex:1;color:#e8e8e8}}
  .ar-arrow{{font-size:14px;color:#555}}
  .watchlist{{margin-bottom:40px}}
  .wl-item{{display:flex;align-items:center;gap:12px;padding:9px 12px;border-radius:6px;margin-bottom:4px}}
  .wl-done{{background:rgba(249,115,22,0.08);}}
  .wl-next{{background:#1e1e1e;border:1px solid #333}}
  .wl-pending{{background:transparent}}
  .wl-num{{font-size:12px;color:#666;width:20px;text-align:center;flex-shrink:0}}
  .wl-done .wl-num{{color:#f97316}}
  .wl-next .wl-num{{color:#f97316;font-weight:700}}
  .wl-ticker{{font-size:14px;font-weight:700;width:56px;flex-shrink:0;color:#e8e8e8}}
  .wl-name{{font-size:13px;color:#aaa;flex:1}}
  .wl-subcat{{font-size:11px;color:#888;width:160px;flex-shrink:0}}
  .wl-cat{{font-size:11px;color:#666;border:1px solid #2a2a2a;border-radius:999px;padding:2px 8px;flex-shrink:0}}
  .wl-done .wl-ticker{{color:#f97316}}
  .wl-done .wl-cat{{border-color:rgba(249,115,22,0.3);color:#f97316}}
  .wl-next .wl-ticker{{color:#fff}}
  .footer{{font-size:12px;color:#555;text-align:center;padding-top:32px;border-top:1px solid #2a2a2a}}
  /* Macro dashboard */
  .macro-dash{{margin-bottom:40px}}
  .macro-cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:8px}}
  .mc{{background:#1e1e1e;border:1px solid #2a2a2a;border-radius:8px;padding:16px 18px}}
  .mc-label{{font-size:10px;color:#aaa;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px}}
  .mc-value{{font-size:22px;font-weight:700;color:#fff;margin-bottom:2px}}
  .mc-sub{{font-size:11px;color:#666;margin-bottom:6px}}
  .mc-next{{font-size:11px;color:#555;border-top:1px solid #272727;padding-top:6px;margin-top:4px}}
  .mc-next span{{color:#f97316}}
  .mc-why{{font-size:11px;color:#555;line-height:1.5;margin-top:4px;font-style:italic}}
  /* Framework section */
  .about{{margin-bottom:48px}}
  .about-intro{{font-size:14px;color:#aaa;line-height:1.7;margin-bottom:24px}}
  .framework-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px}}
  .fw-card{{background:#1e1e1e;border:1px solid #2a2a2a;border-radius:8px;padding:20px 22px;border-left:3px solid #f97316}}
  .fw-title{{font-size:13px;font-weight:700;color:#fff;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.06em}}
  .fw-sub{{font-size:11px;color:#f97316;margin-bottom:12px;font-weight:600}}
  .fw-item{{font-size:12px;color:#aaa;padding:5px 0;border-bottom:1px solid #222;display:flex;flex-direction:column;gap:2px}}
  .fw-item:last-child{{border-bottom:none}}
  .fw-item-label{{font-weight:600;color:#ccc;font-size:12px}}
  .fw-item-examples{{font-size:11px;color:#666}}
  .method-box{{background:#1e1e1e;border:1px solid #2a2a2a;border-radius:8px;padding:20px 22px;margin-top:4px}}
  .method-title{{font-size:12px;font-weight:700;color:#aaa;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px}}
  .method-steps{{display:flex;gap:12px;flex-wrap:wrap}}
  .method-step{{background:#272727;border-radius:6px;padding:8px 14px;font-size:12px;color:#ccc;display:flex;align-items:center;gap:8px}}
  .method-step-num{{color:#f97316;font-weight:700;font-size:13px}}
  @media(max-width:700px){{.macro-cards{{grid-template-columns:repeat(2,1fr)}}}}
  @media(max-width:600px){{.latest-ticker{{font-size:36px}}.stats-bar{{gap:12px}}.framework-grid{{grid-template-columns:1fr}}.wl-subcat{{display:none}}.macro-cards{{grid-template-columns:1fr}}}}
</style>
</head>
<body>

<div class="topbar">
  <div style="display:flex;align-items:center;gap:12px">
    <span class="w-mark">W<span>.</span></span>
    <span style="font-size:13px;color:#555">StockPulse</span>
  </div>
  <span style="font-size:12px;color:#555">Updated {today}</span>
</div>

<div class="container">

  <div class="hero">
    <h1>StockPulse</h1>
    <p>One AI stock analysis, every weekday. 25 stocks across the AI ecosystem — built for the long game.</p>
  </div>

  <div class="stats-bar">
    <div class="stat">
      <span class="stat-label">Reports Published</span>
      <span class="stat-value">{len(reports)}</span>
    </div>
    <div class="stat">
      <span class="stat-label">Watchlist Coverage</span>
      <span class="stat-value">{completed} / {total}</span>
    </div>
    <div class="stat">
      <span class="stat-label">Next Up</span>
      <span class="stat-value">{next_stock.get('ticker','—')}</span>
    </div>
  </div>

  <!-- MACRO DASHBOARD -->
  <div class="macro-dash">
    <p class="section-title">Macro Dashboard</p>
    <div class="macro-cards">
      <div class="mc">
        <div class="mc-label">Fear &amp; Greed Index</div>
        <div class="mc-value" style="color:{fg_color(macro['fg_score'])}">{macro['fg_score']}</div>
        <div class="mc-sub">{macro['fg_rating']} · CNN · 0–100</div>
        <div class="mc-why">Sentiment context — signals whether moves are noise or conviction</div>
      </div>
      <div class="mc">
        <div class="mc-label">Fed Funds Rate</div>
        <div class="mc-value">{macro['fed_rate']}</div>
        <div class="mc-sub">Upper target bound</div>
        <div class="mc-next">Next FOMC: <span>{macro['fed_next']}</span></div>
        <div class="mc-why">Direct impact on high-multiple tech valuations</div>
      </div>
      <div class="mc">
        <div class="mc-label">CPI (YoY)</div>
        <div class="mc-value">{macro['cpi_yoy']}</div>
        <div class="mc-sub">All Urban Consumers</div>
        <div class="mc-next">Next release: <span>{macro['cpi_next']}</span></div>
        <div class="mc-why">Inflation → rate expectations → growth stock discount rates</div>
      </div>
      <div class="mc">
        <div class="mc-label">NFP (Last)</div>
        <div class="mc-value">{macro['nfp_change']}</div>
        <div class="mc-sub">Monthly job additions</div>
        <div class="mc-next">Next release: <span>{macro['nfp_next']}</span></div>
        <div class="mc-why">Labour market strength → Fed posture → tech valuations</div>
      </div>
    </div>
  </div>

  {latest_card}

  <div class="archive">
    <p class="section-title">Archive</p>
    {archive_rows}
  </div>

  <!-- ABOUT / FRAMEWORK -->
  <div class="about">
    <p class="section-title">About StockPulse</p>
    <p class="about-intro">
      AI is a secular mega-trend — projected 26–30% CAGR through 2033 as it embeds into manufacturing, healthcare, finance, logistics, and defence.
      Not all AI stocks are equal. StockPulse analyses them through a two-layer framework: <strong style="color:#fff">Enablers</strong> (companies that make AI possible)
      and <strong style="color:#fff">Adopters</strong> (companies using AI to change their products or operations).
    </p>

    <div class="framework-grid">
      <div class="fw-card">
        <div class="fw-title">Enablers</div>
        <div class="fw-sub">Companies that make AI possible</div>
        <div class="fw-item">
          <span class="fw-item-label">Infrastructure Hardware</span>
          <span class="fw-item-examples">Semiconductors (NVDA, AMD, AVGO, TSM) · Chip equipment (ASML, AMAT) · Memory (MU) · Networking (ANET, MRVL)</span>
        </div>
        <div class="fw-item">
          <span class="fw-item-label">Infrastructure Software & Services</span>
          <span class="fw-item-examples">Cloud & AI platforms (META, ORCL, CRM) · Databases (SNOW) · Creative AI (ADBE) · Edge AI (QCOM, ARM)</span>
        </div>
      </div>
      <div class="fw-card">
        <div class="fw-title">Adopters</div>
        <div class="fw-sub">Companies using AI to compete</div>
        <div class="fw-item">
          <span class="fw-item-label">External Product Enhancement</span>
          <span class="fw-item-examples">Cybersecurity (PANW, FTNT) · Medical devices (ISRG) · Enterprise AI (IBM)</span>
        </div>
        <div class="fw-item">
          <span class="fw-item-label">Internal Productivity & Margin</span>
          <span class="fw-item-examples">AI servers & infra (DELL, HPE) · Ad tech & automation (APP)</span>
        </div>
      </div>
    </div>

    <div class="method-box">
      <div class="method-title">How stocks are selected</div>
      <div class="method-steps">
        <div class="method-step"><span class="method-step-num">1</span> Screened from major AI ETFs (QQQ, BOTZ, ARKQ, SMH)</div>
        <div class="method-step"><span class="method-step-num">2</span> Minimum $10B market cap for liquidity</div>
        <div class="method-step"><span class="method-step-num">3</span> Meaningful AI revenue exposure or AI-driven product roadmap</div>
        <div class="method-step"><span class="method-step-num">4</span> Strong analyst coverage (&gt;10 analysts) for data quality</div>
      </div>
    </div>
  </div>

  <div class="watchlist">
    <p class="section-title">Watchlist — 25 AI Stocks</p>
    {watchlist_items}
  </div>

  <div class="footer">
    Built by Wesley with Claude · Not financial advice
  </div>

</div>
</body>
</html>"""

    index_path = os.path.join(SCRIPT_DIR, "index.html")
    with open(index_path, "w") as f:
        f.write(html)
    print(f"Index built: {index_path} ({len(reports)} reports)")

if __name__ == "__main__":
    build_index()
