import os
import math
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, List, Any

import requests
import yfinance as yf

RIYADH_TZ = ZoneInfo("Asia/Riyadh")
NY_TZ = ZoneInfo("America/New_York")

MARKET_SYMBOLS = ["SPY", "QQQ", "DIA", "IWM", "^VIX"]
SECTOR_SYMBOLS = ["XLK", "XLC", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU"]
LEADER_SYMBOLS = ["NVDA", "AMD", "MSFT", "AAPL", "AMZN", "META", "TSLA", "GOOGL", "AVGO", "SMCI"]
SMALL_CAP_SYMBOLS = ["SOPA", "BBAI", "SOUN", "MARA", "RIOT", "IONQ", "PLTR", "OPEN", "RGTI", "QUBT"]

SECTOR_NAMES_AR = {
    "XLK": "التقنية", "XLC": "الاتصالات", "XLF": "البنوك والمال", "XLE": "الطاقة",
    "XLV": "الصحة", "XLI": "الصناعة", "XLY": "استهلاكي كمالي", "XLP": "استهلاكي دفاعي", "XLU": "المرافق",
}

STOCK_SECTOR_AR = {
    "NVDA": "تقنية / شرائح", "AMD": "تقنية / شرائح", "MSFT": "تقنية", "AAPL": "تقنية",
    "AMZN": "استهلاكي / سحابة", "META": "اتصالات / AI", "TSLA": "سيارات / نمو",
    "GOOGL": "اتصالات / AI", "AVGO": "تقنية / شرائح", "SMCI": "تقنية / خوادم",
    "PLTR": "برمجيات / AI", "MARA": "كريبتو", "RIOT": "كريبتو", "SOUN": "AI", "BBAI": "AI",
}

KEYWORDS = {
    "AI": ["ai", "artificial intelligence", "nvidia", "chip", "semiconductor", "data center"],
    "أرباح": ["earnings", "revenue", "guidance", "eps"],
    "صفقات": ["deal", "contract", "partnership", "agreement"],
    "فائدة": ["fed", "rate", "inflation", "cpi", "pce", "yield"],
    "طاقة": ["oil", "energy", "crude", "opec"],
}


def _safe_float(x, default=0.0):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return default
        return float(x)
    except Exception:
        return default


def market_status() -> Dict[str, str]:
    now_riyadh = datetime.now(RIYADH_TZ)
    now_ny = now_riyadh.astimezone(NY_TZ)
    open_ny = now_ny.replace(hour=9, minute=30, second=0, microsecond=0)
    close_ny = now_ny.replace(hour=16, minute=0, second=0, microsecond=0)
    is_weekday = now_ny.weekday() < 5
    if is_weekday and open_ny <= now_ny <= close_ny:
        state = "مفتوح"
    elif is_weekday and now_ny < open_ny:
        state = "قبل الافتتاح"
    else:
        state = "مغلق"
    return {
        "date": now_riyadh.strftime("%Y-%m-%d"),
        "day": now_riyadh.strftime("%A"),
        "riyadh_time": now_riyadh.strftime("%H:%M:%S"),
        "ny_time": now_ny.strftime("%H:%M:%S"),
        "status": state,
        "open_riyadh": open_ny.astimezone(RIYADH_TZ).strftime("%H:%M"),
        "close_riyadh": close_ny.astimezone(RIYADH_TZ).strftime("%H:%M"),
    }


def fetch_quotes(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    data: Dict[str, Dict[str, Any]] = {}
    tickers = yf.Tickers(" ".join(symbols))
    for symbol in symbols:
        try:
            t = tickers.tickers[symbol]
            hist = t.history(period="1mo", interval="1d", auto_adjust=False)
            info = getattr(t, "fast_info", {}) or {}
            if hist.empty:
                continue
            last = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else last
            price = _safe_float(info.get("last_price"), _safe_float(last.get("Close")))
            prev_close = _safe_float(info.get("previous_close"), _safe_float(prev.get("Close")))
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
            volume = int(_safe_float(last.get("Volume")))
            avg_vol = _safe_float(hist["Volume"].tail(20).mean(), 0)
            rvol = volume / avg_vol if avg_vol else 0
            day_high = _safe_float(last.get("High"))
            day_low = _safe_float(last.get("Low"))
            gap_pct = ((_safe_float(last.get("Open")) - prev_close) / prev_close * 100) if prev_close else 0
            data[symbol] = {
                "symbol": symbol.replace("^", ""),
                "raw_symbol": symbol,
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
                "volume": volume,
                "rvol": round(rvol, 2),
                "gap_pct": round(gap_pct, 2),
                "high": round(day_high, 2),
                "low": round(day_low, 2),
                "prev_close": round(prev_close, 2),
            }
        except Exception as exc:
            data[symbol] = {"symbol": symbol.replace("^", ""), "error": str(exc)}
    return data


def classify_strength(change_pct: float, rvol: float = 1.0) -> str:
    if change_pct >= 1.5 or rvol >= 2.5:
        return "قوي جدًا"
    if change_pct >= 0.5 or rvol >= 1.5:
        return "قوي"
    if change_pct <= -1.5:
        return "ضعيف جدًا"
    if change_pct < 0:
        return "ضعيف"
    return "متوسط"


def analyze_market(quotes: Dict[str, Dict[str, Any]], sectors: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    spy = quotes.get("SPY", {})
    qqq = quotes.get("QQQ", {})
    dia = quotes.get("DIA", {})
    iwm = quotes.get("IWM", {})
    vix = quotes.get("^VIX", {})
    positives = sum(1 for x in [spy, qqq, dia, iwm] if _safe_float(x.get("change_pct")) > 0)
    vix_down = _safe_float(vix.get("change_pct")) < 0
    score = 0
    score += 20 if _safe_float(spy.get("change_pct")) > 0 else -10
    score += 25 if _safe_float(qqq.get("change_pct")) > _safe_float(spy.get("change_pct")) else 5
    score += 15 if positives >= 3 else -10
    score += 20 if vix_down else -20
    score += 10 if _safe_float(iwm.get("change_pct")) > 0 else 0
    score = max(0, min(100, score + 30))
    if score >= 70:
        intent, mood = "كول", "Risk-On"
    elif score <= 40:
        intent, mood = "بوت", "Risk-Off"
    else:
        intent, mood = "محايد", "Neutral"
    leader_sector = None
    valid_sectors = [v for v in sectors.values() if "error" not in v]
    if valid_sectors:
        leader_sector = max(valid_sectors, key=lambda x: _safe_float(x.get("change_pct")))
    return {
        "intent": intent,
        "mood": mood,
        "confidence": round(score),
        "leader_sector": leader_sector["symbol"] if leader_sector else "غير واضح",
        "leader_sector_ar": SECTOR_NAMES_AR.get(leader_sector["symbol"], leader_sector["symbol"]) if leader_sector else "غير واضح",
        "participation": f"{positives}/4 مؤشرات رئيسية إيجابية",
        "vix_status": "داعم" if vix_down else "ضاغط",
        "summary": build_market_sentence(intent, mood, leader_sector, positives, vix_down),
    }


def build_market_sentence(intent, mood, leader_sector, positives, vix_down) -> str:
    leader = SECTOR_NAMES_AR.get(leader_sector["symbol"], leader_sector["symbol"]) if leader_sector else "غير واضح"
    vix_text = "مع هدوء في الخوف" if vix_down else "لكن الخوف مرتفع"
    breadth = "مشاركة جيدة" if positives >= 3 else "مشاركة ضعيفة/انتقائية"
    return f"السوق يميل إلى {intent} ({mood}) بقيادة {leader}، {breadth}، {vix_text}."


def fetch_news(symbols: List[str]) -> List[Dict[str, Any]]:
    finnhub_key = os.getenv("FINNHUB_API_KEY", "").strip()
    news = []
    if finnhub_key:
        for s in symbols[:8]:
            try:
                url = f"https://finnhub.io/api/v1/company-news?symbol={s}&from={datetime.utcnow().date()}&to={datetime.utcnow().date()}&token={finnhub_key}"
                for item in requests.get(url, timeout=6).json()[:2]:
                    news.append({"symbol": s, "headline": item.get("headline", ""), "source": item.get("source", "Finnhub")})
            except Exception:
                pass
    if not news:
        for s in symbols[:8]:
            try:
                items = yf.Ticker(s).news or []
                for it in items[:2]:
                    title = it.get("title") or it.get("content", {}).get("title", "")
                    publisher = it.get("publisher") or it.get("content", {}).get("provider", {}).get("displayName", "Yahoo")
                    if title:
                        news.append({"symbol": s, "headline": title, "source": publisher})
            except Exception:
                pass
    return news[:20]


def detect_catalysts(news: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {k: 0 for k in KEYWORDS}
    for n in news:
        text = (n.get("headline") or "").lower()
        for label, kws in KEYWORDS.items():
            if any(k in text for k in kws):
                counts[label] += 1
    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    dominant = top[0][0] if top and top[0][1] > 0 else "غير واضح"
    return {"dominant": dominant, "counts": counts}


def fetch_social_trends() -> List[Dict[str, Any]]:
    try:
        r = requests.get("https://api.stocktwits.com/api/2/trending/symbols.json", timeout=6)
        payload = r.json()
        symbols = payload.get("symbols", [])[:10]
        return [{"symbol": s.get("symbol"), "title": s.get("title", ""), "source": "StockTwits"} for s in symbols]
    except Exception:
        # احتياطي مجاني: رموز ثابتة عالية النشاط إذا تعطل مصدر الترند
        return [{"symbol": s, "title": "قائمة مراقبة احتياطية", "source": "Fallback"} for s in ["NVDA", "TSLA", "AMD", "AAPL", "AMZN"]]


def flow_proxy(q: Dict[str, Any]) -> Dict[str, Any]:
    ch = _safe_float(q.get("change_pct"))
    rv = _safe_float(q.get("rvol"))
    gap = abs(_safe_float(q.get("gap_pct")))
    score = 0
    score += 35 if abs(ch) >= 3 else 20 if abs(ch) >= 1 else 5
    score += 35 if rv >= 3 else 20 if rv >= 1.5 else 5
    score += 20 if gap >= 3 else 10 if gap >= 1 else 0
    score += 10 if ch > 0 else 0
    level = "قوي" if score >= 70 else "متوسط" if score >= 40 else "ضعيف"
    return {"score": min(score, 100), "level": level}


def stage_and_move(q: Dict[str, Any], is_small=False):
    ch = _safe_float(q.get("change_pct"))
    rv = _safe_float(q.get("rvol"))
    gap = abs(_safe_float(q.get("gap_pct")))
    if ch >= 25 and rv >= 5:
        stage = "نهاية" if gap > 20 else "منتصف"
        move = "Pump"
    elif ch >= 5 and rv >= 2:
        stage = "بداية"
        move = "Breakout"
    elif ch > 0 and rv >= 1:
        stage = "نظيف"
        move = "Trend"
    else:
        stage = "ضعيف"
        move = "غير واضح"
    if is_small and ch >= 15 and rv >= 3 and gap < 15:
        stage = "بداية"
    return stage, move


def score_stock(q: Dict[str, Any], is_small=False) -> int:
    ch = _safe_float(q.get("change_pct"))
    rv = _safe_float(q.get("rvol"))
    gap = abs(_safe_float(q.get("gap_pct")))
    score = 0
    score += min(25, max(0, abs(ch) * 3))
    score += 25 if rv >= 3 else 18 if rv >= 2 else 10 if rv >= 1 else 0
    score += 15 if gap >= 5 else 10 if gap >= 2 else 3
    score += 15 if ch > 0 else 5
    stage, move = stage_and_move(q, is_small)
    score += {"بداية": 20, "نظيف": 15, "منتصف": 10, "نهاية": 0}.get(stage, 0)
    return int(max(0, min(100, score)))


def enrich_stocks(quotes: Dict[str, Dict[str, Any]], is_small=False) -> List[Dict[str, Any]]:
    rows = []
    for sym, q in quotes.items():
        if "error" in q:
            continue
        stage, move = stage_and_move(q, is_small)
        score = score_stock(q, is_small)
        fp = flow_proxy(q)
        if score >= 80:
            status = "قوي"
        elif score >= 60:
            status = "مراقبة"
        else:
            status = "ضعيف"
        risk = "عالية" if is_small or abs(_safe_float(q.get("change_pct"))) > 8 else "متوسطة"
        rows.append({**q, "sector": STOCK_SECTOR_AR.get(q["symbol"], "غير مصنف"), "stage": stage, "move_type": move,
                     "reentry": "نعم" if stage in ["نظيف", "منتصف"] else "لا", "score": score,
                     "flow": fp["level"], "risk": risk, "status": status})
    return sorted(rows, key=lambda x: x["score"], reverse=True)


def build_dashboard() -> Dict[str, Any]:
    all_quotes_symbols = list(dict.fromkeys(MARKET_SYMBOLS + SECTOR_SYMBOLS + LEADER_SYMBOLS + SMALL_CAP_SYMBOLS))
    quotes_all = fetch_quotes(all_quotes_symbols)
    market_quotes = {s: quotes_all.get(s, {}) for s in MARKET_SYMBOLS}
    sector_quotes = {s: quotes_all.get(s, {}) for s in SECTOR_SYMBOLS}
    leader_quotes = {s: quotes_all.get(s, {}) for s in LEADER_SYMBOLS}
    small_quotes = {s: quotes_all.get(s, {}) for s in SMALL_CAP_SYMBOLS}

    market = analyze_market(market_quotes, sector_quotes)
    leaders = enrich_stocks(leader_quotes, False)
    smallcaps = enrich_stocks(small_quotes, True)
    trends = fetch_social_trends()
    news = fetch_news(LEADER_SYMBOLS + SMALL_CAP_SYMBOLS)
    catalysts = detect_catalysts(news)
    strongest = sorted(leaders + smallcaps, key=lambda x: x["score"], reverse=True)[:5]
    social_symbols = {x.get("symbol") for x in trends}
    social_overlap = [x["symbol"] for x in strongest if x["symbol"] in social_symbols]
    sentiment = "إيجابي" if market["intent"] == "كول" and strongest and strongest[0]["change_pct"] > 0 else "سلبي" if market["intent"] == "بوت" else "منقسم"
    impression = {
        "market_intent": market["intent"],
        "mood": market["mood"],
        "liquidity": f"تدفق نحو {market['leader_sector_ar']}",
        "catalyst": catalysts["dominant"],
        "trend_symbols": [x.get("symbol") for x in trends[:5]],
        "sentiment": sentiment,
        "flow_proxy": "قوي" if strongest and strongest[0]["score"] >= 80 else "متوسط",
        "strongest_symbols": [x["symbol"] for x in strongest[:5]],
        "social_overlap": social_overlap,
        "judgment": f"{market['summary']} أقوى الرموز المتفاعلة: {', '.join([x['symbol'] for x in strongest[:3]])}. الترند الاجتماعي: {', '.join([x.get('symbol') for x in trends[:3] if x.get('symbol')])}."
    }
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "clock": market_status(),
        "impression": impression,
        "market": market,
        "market_rows": list(market_quotes.values()),
        "sectors": sorted([v for v in sector_quotes.values() if "error" not in v], key=lambda x: x.get("change_pct", 0), reverse=True),
        "leaders": leaders,
        "smallcaps": smallcaps,
        "trends": trends,
        "news": news,
        "data_note": "الأسعار من Yahoo Finance/yfinance. الأخبار من Finnhub إذا أضفت مفتاح API وإلا Yahoo Finance. الترند من StockTwits عند توفره."
    }
