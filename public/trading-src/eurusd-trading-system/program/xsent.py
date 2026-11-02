"""Optional X (Twitter) sentiment input. It uses the official API v2 recent search with the user's bearer token
(env X_BEARER_TOKEN, never printed or logged). It runs at most 1 call per cycle, rotating through the instruments
with max_results=25. On 401/402/403/429 or a missing token it logs 'X sentiment unavailable (...)' once per state
change to journal/assumptions.jsonl, backs off 6 h, and the engine continues without it. If credits come back it
resumes automatically. Only aggregate counts and a crude lexicon score are stored, never post text or user names.
Pump / guaranteed-profit / signal-selling posts are filtered out and counted. This is noisy sentiment only and
is NOT a trade trigger in any v1 hypothesis."""
import json
import os
import re
import time

import requests

import journal as J

P = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(P, "state", "xsent_state.json")
URL = "https://api.x.com/2/tweets/search/recent"
BACKOFF_S = 6 * 3600
QUERIES = {
    "EURUSD": '(EURUSD OR "EUR/USD" OR #EURUSD) -is:retweet lang:en',
    "GBPUSD": '(GBPUSD OR "GBP/USD" OR cable sterling) -is:retweet lang:en',
    "USDJPY": '(USDJPY OR "USD/JPY" OR #USDJPY) -is:retweet lang:en',
    "AUDUSD": '(AUDUSD OR "AUD/USD") -is:retweet lang:en',
    "US500": '("S&P 500" OR SPX OR $SPY OR #SPX) -is:retweet lang:en',
    "XAUUSD": '(XAUUSD OR "gold price" OR #gold) -is:retweet lang:en',
}
PUMP = re.compile(r"(guarantee|100% ?(win|profit|accura)|sure ?shot|risk[- ]free|signals? (group|channel|service)|join (my|our)|"
                  r"telegram|whatsapp|vip|dm me|free signals|copy (my )?trades|account manag|passive income|\b\d{3,}% (profit|return)|"
                  r"pips? (daily|every day)|to the moon|🚀{2,})", re.I)
BULL = re.compile(r"\b(bull\w*|long(ing)?|buy(ing)?|rall\w*|breakout|higher|support holds?|upside|bid)\b", re.I)
BEAR = re.compile(r"\b(bear\w*|short(ing)?|sell(ing)?|dump\w*|breakdown|lower|resistance|downside|offered|crash\w*)\b", re.I)


def _st():
    try: return json.load(open(STATE))
    except Exception: return dict(i=0, status="unknown", next_try=0)


def _save(s): json.dump(s, open(STATE, "w"))


def _unavailable(s, reason):
    if s.get("status") != reason:
        J.append(J.ASSUME, dict(type="assumption", key="x_sentiment", value=f"X sentiment unavailable ({reason})",
                                detail="engine continues without X input; next re-check in <= 6 h"))
    s["status"] = reason; s["next_try"] = time.time() + BACKOFF_S; _save(s)
    return dict(x_status=f"unavailable ({reason})")


def poll():
    """blocking (run in a thread). At most ONE API call."""
    s = _st(); now = time.time()
    tok = os.environ.get("X_BEARER_TOKEN")
    if not tok: return _unavailable(s, "no token")
    if now < s.get("next_try", 0): return dict(x_status=f"backoff ({s.get('status')}) until {J.now_iso(s['next_try'])}")
    syms = list(QUERIES); sym = syms[s.get("i", 0) % len(syms)]; s["i"] = s.get("i", 0) + 1
    try:
        r = requests.get(URL, headers={"Authorization": f"Bearer {tok}"}, timeout=20,
                         params=dict(query=QUERIES[sym], max_results=25, **{"tweet.fields": "created_at,public_metrics"}))
    except Exception as e:
        s["next_try"] = now + 1800; _save(s); return dict(x_status=f"network error {type(e).__name__}")
    if r.status_code in (402, 429):
        return _unavailable(s, "credits" if r.status_code == 402 else "rate limit 429")
    if r.status_code in (401, 403):
        return _unavailable(s, f"auth {r.status_code}")
    if r.status_code != 200:
        s["next_try"] = now + 1800; _save(s); return dict(x_status=f"http {r.status_code}")
    data = r.json().get("data", []) or []
    n = len(data); pump = sum(1 for d in data if PUMP.search(d.get("text", "")))
    clean = [d for d in data if not PUMP.search(d.get("text", ""))]
    bull = sum(1 for d in clean if BULL.search(d.get("text", ""))); bear = sum(1 for d in clean if BEAR.search(d.get("text", "")))
    score = (bull - bear) / max(1, bull + bear)
    if s.get("status") != "ok":
        J.append(J.ASSUME, dict(type="assumption", key="x_sentiment", value="X sentiment available (recent search OK)"))
    s["status"] = "ok"; s["next_try"] = now + 60; _save(s)
    rec = dict(type="x_sentiment", symbol=sym, posts=n, pump_filtered=pump, used=len(clean), bull=bull, bear=bear,
               score=round(score, 3), note="noisy sentiment only; aggregates only, no post text stored")
    J.append(J.NEWS, rec)
    return dict(x_status="ok", **{k: rec[k] for k in ("symbol", "posts", "score")})
