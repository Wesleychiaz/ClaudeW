#!/usr/bin/env python3
"""Scans reports/ and rebuilds stockpulse/index.html"""

import os
import json
import re
import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(SCRIPT_DIR, "reports")
WATCHLIST_PATH = os.path.join(SCRIPT_DIR, "watchlist.json")

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
            reports.append({"date": m.group(1), "ticker": m.group(2), "filename": f})
    reports.sort(key=lambda x: x["date"], reverse=True)
    return reports

def build_index():
    reports = get_reports()
    idx, total, next_stock = get_watchlist_progress()
    completed = idx
    today = datetime.date.today().isoformat()

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
  @media(max-width:600px){{.latest-ticker{{font-size:36px}}.stats-bar{{gap:12px}}.framework-grid{{grid-template-columns:1fr}}.wl-subcat{{display:none}}}}
</style>
</head>
<body>

<div class="topbar">
  <div style="display:flex;align-items:center;gap:12px">
    <span class="w-mark">W<span>.</span></span>
    <a href="../" class="back">← Wesley's Projects</a>
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
