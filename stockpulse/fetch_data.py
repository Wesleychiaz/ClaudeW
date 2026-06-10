#!/usr/bin/env python3
"""
StockPulse data fetcher — pulls stock data and macro context.
Outputs JSON to stdout for Claude Code to consume and generate analysis.
Usage: python3 fetch_data.py [TICKER]
If no ticker provided, reads watchlist.json and picks the next stock.
"""

import json
import sys
import os
import datetime
import requests

try:
    import yfinance as yf
except ImportError:
    print(json.dumps({"error": "yfinance not installed. Run: pip3 install yfinance"}))
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WATCHLIST_PATH = os.path.join(SCRIPT_DIR, "watchlist.json")


def get_fear_greed():
    urls = [
        "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
        "https://fear-and-greed-index.p.rapidapi.com/v1/fgi",
    ]
    # Try CNN endpoint first
    try:
        r = requests.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.cnn.com/"},
            timeout=10
        )
        if r.status_code == 200 and r.text.strip():
            data = r.json()
            score = round(data["fear_and_greed"]["score"])
            rating = data["fear_and_greed"]["rating"].replace("_", " ").title()
            prev = round(data["fear_and_greed"]["previous_close"])
            return {"score": score, "rating": rating, "previous_close": prev}
    except Exception:
        pass
    # Fallback: alternative.me (crypto-based but commonly used as proxy)
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        data = r.json()
        score = int(data["data"][0]["value"])
        rating = data["data"][0]["value_classification"]
        return {"score": score, "rating": rating, "note": "via alternative.me"}
    except Exception as e:
        return {"score": "N/A", "rating": "N/A", "error": str(e)}


def get_stock_data(ticker):
    t = yf.Ticker(ticker)
    info = t.info

    # Price performance — use yfinance download for reliability
    def pct_change(ticker_sym, period=None, start=None):
        try:
            import yfinance as _yf
            kwargs = {"period": period} if period else {"start": start, "end": datetime.date.today().isoformat()}
            h = _yf.download(ticker_sym, progress=False, auto_adjust=True, **kwargs)
            if h.empty or len(h) < 2:
                return "N/A"
            close = h["Close"].dropna()
            if len(close) < 2:
                return "N/A"
            first, last = float(close.iloc[0]), float(close.iloc[-1])
            return round((last / first - 1) * 100, 2) if first else "N/A"
        except Exception:
            return "N/A"

    current_price = info.get("currentPrice") or info.get("regularMarketPrice") or "N/A"
    prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
    day_change_pct = round((current_price / prev_close - 1) * 100, 2) if prev_close and isinstance(current_price, (int, float)) else "N/A"

    # Recent news headlines
    news_items = []
    try:
        news = t.news
        if news:
            for n in news[:6]:
                content = n.get("content", {})
                title = content.get("title", "") if isinstance(content, dict) else ""
                pub = content.get("pubDate", "") if isinstance(content, dict) else ""
                if title:
                    news_items.append({"title": title, "date": pub[:10] if pub else ""})
    except Exception:
        pass

    return {
        "ticker": ticker,
        "name": info.get("longName", ticker),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "price": current_price,
        "day_change_pct": day_change_pct,
        "market_cap_b": round(info.get("marketCap", 0) / 1e9, 2) if info.get("marketCap") else "N/A",
        "beta": info.get("beta", "N/A"),
        "52w_high": info.get("fiftyTwoWeekHigh", "N/A"),
        "52w_low": info.get("fiftyTwoWeekLow", "N/A"),
        "avg_volume_m": round(info.get("averageVolume", 0) / 1e6, 2) if info.get("averageVolume") else "N/A",
        "pe_ttm": round(info.get("trailingPE", 0), 1) if info.get("trailingPE") else "N/A",
        "forward_pe": round(info.get("forwardPE", 0), 1) if info.get("forwardPE") else "N/A",
        "ps_ratio": round(info.get("priceToSalesTrailing12Months", 0), 1) if info.get("priceToSalesTrailing12Months") else "N/A",
        "pb_ratio": round(info.get("priceToBook", 0), 1) if info.get("priceToBook") else "N/A",
        "gross_margin_pct": round(info.get("grossMargins", 0) * 100, 1) if info.get("grossMargins") else "N/A",
        "operating_margin_pct": round(info.get("operatingMargins", 0) * 100, 1) if info.get("operatingMargins") else "N/A",
        "net_margin_pct": round(info.get("profitMargins", 0) * 100, 1) if info.get("profitMargins") else "N/A",
        "revenue_growth_yoy_pct": round(info.get("revenueGrowth", 0) * 100, 1) if info.get("revenueGrowth") else "N/A",
        "earnings_growth_yoy_pct": round(info.get("earningsGrowth", 0) * 100, 1) if info.get("earningsGrowth") else "N/A",
        "revenue_ttm_b": round(info.get("totalRevenue", 0) / 1e9, 2) if info.get("totalRevenue") else "N/A",
        "free_cash_flow_b": round(info.get("freeCashflow", 0) / 1e9, 2) if info.get("freeCashflow") else "N/A",
        "cash_b": round(info.get("totalCash", 0) / 1e9, 2) if info.get("totalCash") else "N/A",
        "debt_b": round(info.get("totalDebt", 0) / 1e9, 2) if info.get("totalDebt") else "N/A",
        "analyst_count": info.get("numberOfAnalystOpinions", "N/A"),
        "recommendation": info.get("recommendationKey", "N/A"),
        "target_mean_price": round(info.get("targetMeanPrice", 0), 2) if info.get("targetMeanPrice") else "N/A",
        "target_high_price": round(info.get("targetHighPrice", 0), 2) if info.get("targetHighPrice") else "N/A",
        "target_low_price": round(info.get("targetLowPrice", 0), 2) if info.get("targetLowPrice") else "N/A",
        "description": info.get("longBusinessSummary", "")[:400] if info.get("longBusinessSummary") else "",
        "performance": {
            "1d": day_change_pct,
            "5d": pct_change(ticker, period="5d"),
            "1m": pct_change(ticker, period="1mo"),
            "3m": pct_change(ticker, period="3mo"),
            "6m": pct_change(ticker, period="6mo"),
            "ytd": pct_change(ticker, start=f"{datetime.date.today().year}-01-01"),
            "1y": pct_change(ticker, period="1y")
        },
        "recent_news": news_items
    }


def advance_watchlist():
    with open(WATCHLIST_PATH) as f:
        wl = json.load(f)

    idx = wl["current_index"]
    stock = wl["stocks"][idx]

    wl["current_index"] = (idx + 1) % len(wl["stocks"])
    wl["last_run"] = datetime.date.today().isoformat()

    with open(WATCHLIST_PATH, "w") as f:
        json.dump(wl, f, indent=2)

    return stock, idx + 1, len(wl["stocks"])


def main():
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        report_num = "—"
        total = "—"
        # Look up in watchlist so category/sector/subcategory are populated
        stock_meta = {"ticker": ticker, "name": ticker, "sector": "N/A", "category": "N/A", "subcategory": ""}
        try:
            with open(WATCHLIST_PATH) as f:
                wl = json.load(f)
            for s in wl["stocks"]:
                if s["ticker"] == ticker:
                    stock_meta = s
                    total = len(wl["stocks"])
                    break
        except Exception:
            pass
    else:
        stock_meta, report_num, total = advance_watchlist()
        ticker = stock_meta["ticker"]

    print(f"Fetching data for {ticker}...", file=sys.stderr)

    output = {
        "meta": {
            "ticker": ticker,
            "name": stock_meta.get("name", ticker),
            "watchlist_category": stock_meta.get("category", "N/A"),
            "watchlist_sector": stock_meta.get("sector", "N/A"),
            "watchlist_subcategory": stock_meta.get("subcategory", ""),
            "report_number": report_num,
            "total_stocks": total,
            "generated_date": datetime.date.today().isoformat(),
            "generated_time_sgt": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        },
        "macro": {
            "fear_greed": get_fear_greed()
        },
        "stock": get_stock_data(ticker)
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
