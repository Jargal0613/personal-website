"""Public news inputs for the paper program: official central-bank / statistics RSS + free headline RSS, and the
ForexFactory calendar that the news recorder already maintains (data/news_schedule.json, no extra FF requests).
Headlines are stored as title/link/time/tags only. They are context for the journal, not trade signals."""
import hashlib
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

import journal as J

P = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(P)
SEEN = os.path.join(P, "state", "news_seen.json")
SCHED = os.path.join(ROOT, "data", "news_schedule.json")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
FEEDS = {  # all public, no login. Official sources first.
    "fed": "https://www.federalreserve.gov/feeds/press_all.xml",
    "ecb": "https://www.ecb.europa.eu/rss/press.html",
    "boe": "https://www.bankofengland.co.uk/rss/news",
    "boj": "https://www.boj.or.jp/en/rss/whatsnew.xml",
    "rba": "https://www.rba.gov.au/rss/rss-cb-media-releases.xml",
    "fxstreet": "https://www.fxstreet.com/rss/news",
    "investing": "https://www.investing.com/rss/news_1.rss",
    "marketwatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
}
TAGS = {
    "USD": r"\b(fed|fomc|powell|u\.?s\.? (cpi|inflation|jobs|payrolls|gdp)|nonfarm|treasury|dollar|usd)\b",
    "EUR": r"\b(ecb|lagarde|euro ?zone|eurozone|euro\b|eur/?usd|bund)\b",
    "GBP": r"\b(boe|bank of england|bailey|sterling|pound|gbp|gilt)\b",
    "JPY": r"\b(boj|bank of japan|ueda|yen|jpy|japan)\b",
    "AUD": r"\b(rba|reserve bank of australia|aussie|aud)\b",
    "XAU": r"\b(gold|xau|bullion)\b",
    "US500": r"\b(s&p ?500|wall street|stocks|equities|nasdaq|dow)\b",
    "rates": r"\b(rate (cut|hike|decision)|interest rate|monetary policy|minutes)\b",
    "data": r"\b(cpi|pmi|gdp|payrolls|retail sales|unemployment|inflation|ppi|pce)\b",
    "risk": r"\b(war|tariff|sanction|crisis|default|shutdown|attack|escalat)\w*",
}


def _load_seen():
    try: return json.load(open(SEEN))
    except Exception: return {}


def _tags(title):
    t = title.lower()
    return [k for k, rx in TAGS.items() if re.search(rx, t)]


def _items(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"): continue
        d = {c.tag.split("}")[-1]: (c.text or "").strip() for c in it}
        link = d.get("link") or next((c.attrib.get("href") for c in it if c.tag.split("}")[-1] == "link"), "")
        pub = d.get("pubDate") or d.get("date") or d.get("published") or d.get("updated") or ""
        out.append(dict(title=re.sub(r"\s+", " ", d.get("title", ""))[:300], link=link, pub=pub))
    return out


def _pub_ts(s):
    try: return parsedate_to_datetime(s).timestamp()
    except Exception:
        try:
            from datetime import datetime
            return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
        except Exception: return None


def poll_rss(max_age_h=48):
    """blocking (run in a thread). Returns summary dict; new headlines are appended to journal/news.jsonl."""
    seen = _load_seen(); now = time.time(); new = 0; errors = {}; counts = {}
    for src, url in FEEDS.items():
        try:
            r = requests.get(url, headers=UA, timeout=20)
            r.raise_for_status()
            for it in _items(r.content):
                key = hashlib.sha1((src + it["link"] + it["title"]).encode()).hexdigest()[:16]
                if key in seen: continue
                ts = _pub_ts(it["pub"])
                seen[key] = now
                if ts is not None and now - ts > max_age_h * 3600: continue
                tg = _tags(it["title"])
                J.append(J.NEWS, dict(type="headline", source=src, official=src in ("fed", "ecb", "boe", "boj", "rba"),
                                      published_utc=J.now_iso(ts) if ts else it["pub"], title=it["title"], link=it["link"], tags=tg))
                new += 1
                for t in tg: counts[t] = counts.get(t, 0) + 1
        except Exception as e:
            errors[src] = str(e)[:120]
    seen = {k: v for k, v in seen.items() if now - v < 14 * 86400}
    json.dump(seen, open(SEEN, "w"))
    return dict(new_headlines=new, tag_counts=counts, feed_errors=errors)


def calendar(now=None, ahead_h=24, back_min=30):
    """upcoming high-impact releases from the recorder's FF-based schedule (no extra requests)."""
    now = now or time.time()
    try: d = json.load(open(SCHED))
    except Exception: return []
    return [e for e in d.get("events", []) if now - back_min * 60 <= e["t"] <= now + ahead_h * 3600]


def in_news_window(t, before_s=120, after_s=900):
    try: d = json.load(open(SCHED))
    except Exception: return None
    for e in d.get("events", []):
        if e["t"] - before_s <= t <= e["t"] + after_s: return e
    return None


def log_calendar_once():
    seen = _load_seen(); n = 0
    for e in calendar(ahead_h=7 * 24, back_min=0):
        k = f"cal{e['t']}{e['title']}"
        if k in seen: continue
        seen[k] = time.time(); n += 1
        J.append(J.NEWS, dict(type="calendar", source="forexfactory(via recorder schedule)", release_utc=J.now_iso(e["t"]),
                              currency=e["cur"], title=e["title"], impact="high"))
    json.dump(seen, open(SEEN, "w"))
    return n
