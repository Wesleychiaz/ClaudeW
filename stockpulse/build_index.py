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
            watchlist_items += f'<div class="wl-item {cls}"><span class="wl-num">{label}</span><span class="wl-ticker">{stock["ticker"]}</span><span class="wl-name">{stock["name"]}</span><span class="wl-cat">{stock["category"]}</span></div>'
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
  body{{background:#0f0f0f;color:#fff;font-family:'Inter',system-ui,sans-serif;line-height:1.6}}
  a{{color:inherit;text-decoration:none}}
  .topbar{{background:#1a1a1a;border-bottom:1px solid #2a2a2a;padding:14px 32px;display:flex;align-items:center;justify-content:space-between}}
  .w-mark{{font-size:16px;font-weight:900;color:#fff;letter-spacing:-0.02em;margin-right:12px}}
  .w-mark span{{color:#f97316}}
  .back{{font-size:13px;color:#888}}
  .back:hover{{color:#fff}}
  .container{{max-width:860px;margin:0 auto;padding:48px 24px 80px}}
  .hero{{margin-bottom:40px}}
  .hero h1{{font-size:36px;font-weight:900;letter-spacing:-0.03em;margin-bottom:8px}}
  .hero p{{font-size:15px;color:#888}}
  .stats-bar{{display:flex;gap:16px;margin:24px 0;flex-wrap:wrap}}
  .stat{{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;padding:12px 20px;display:flex;flex-direction:column;gap:3px}}
  .stat-label{{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.08em}}
  .stat-value{{font-size:22px;font-weight:700}}
  .latest-card{{display:block;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;padding:28px 32px;margin-bottom:32px;transition:border-color 0.2s}}
  .latest-card:hover{{border-color:#f97316}}
  .latest-label{{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px}}
  .latest-ticker{{font-size:48px;font-weight:900;letter-spacing:-0.03em;margin-bottom:4px}}
  .latest-sub{{font-size:14px;color:#f97316}}
  .section-title{{font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#888;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid #2a2a2a}}
  .archive{{margin-bottom:40px}}
  .archive-row{{display:flex;align-items:center;gap:16px;padding:12px 0;border-bottom:1px solid #2a2a2a;transition:color 0.15s}}
  .archive-row:hover{{color:#f97316}}
  .ar-date{{font-size:12px;color:#555;width:100px;flex-shrink:0}}
  .ar-ticker{{font-size:15px;font-weight:600;flex:1}}
  .ar-arrow{{font-size:14px;color:#555}}
  .watchlist{{margin-bottom:40px}}
  .wl-item{{display:flex;align-items:center;gap:12px;padding:9px 12px;border-radius:6px;margin-bottom:4px}}
  .wl-done{{background:rgba(249,115,22,0.06);}}
  .wl-next{{background:#1a1a1a;border:1px solid #2a2a2a}}
  .wl-pending{{background:transparent}}
  .wl-num{{font-size:12px;color:#555;width:20px;text-align:center;flex-shrink:0}}
  .wl-done .wl-num{{color:#f97316}}
  .wl-next .wl-num{{color:#f97316;font-weight:700}}
  .wl-ticker{{font-size:14px;font-weight:700;width:56px;flex-shrink:0}}
  .wl-name{{font-size:13px;color:#888;flex:1}}
  .wl-cat{{font-size:11px;color:#555;border:1px solid #2a2a2a;border-radius:999px;padding:2px 8px;flex-shrink:0}}
  .wl-done .wl-ticker{{color:#f97316}}
  .wl-next .wl-ticker{{color:#fff}}
  .footer{{font-size:12px;color:#555;text-align:center;padding-top:32px;border-top:1px solid #2a2a2a}}
  @media(max-width:600px){{.latest-ticker{{font-size:36px}}.stats-bar{{gap:12px}}}}
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
    <p>One AI stock analysis, every weekday. Focused on the AI ecosystem — enablers and adopters.</p>
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
