"""Live news-window tick recorder (READ-ONLY, DEMO host only, no order code).

Subscribes to EURUSD, GBPUSD and USDJPY spot quotes on the cTrader DEMO connection. Every quote (UTC ms, bid, ask)
is written to data/news_ticks/YYYY-MM-DD.csv, but ONLY inside these windows:
  - news: -10 to +30 min around each scheduled HIGH-impact USD/EUR release, plus the EUR flash PMIs
    (medium on FF). Overlapping windows are merged.
  - baseline: one pseudo-random 40-min window per weekday, 01:00-20:00 UTC, >= 60 min from any news window
Schedule source: the ForexFactory weekly JSON feed (nfs.faireconomy.media/ff_calendar_thisweek.json) plus the
ForexFactory month page(s). Refreshed at start and then every 24h (the feed every 6h), at most a few requests a
day, with the result cached in data/news_schedule.json. If a refresh fails, the cached schedule is reused.
Requests sent: ApplicationAuth, GetAccountListByAccessToken, AccountAuth, SymbolsList, SubscribeSpots. Nothing else.
Credentials come from the environment or the chmod-600 .env and are never printed.
Heartbeat: data/news_recorder.heartbeat is touched every 30 s while quotes flow (or while the market is closed).
The supervisor restarts the process if the heartbeat goes stale.
"""
import csv
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from ctrader_open_api import Client, TcpProtocol, EndPoints, Protobuf
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq, ProtoOAApplicationAuthRes,
    ProtoOAGetAccountListByAccessTokenReq, ProtoOAGetAccountListByAccessTokenRes,
    ProtoOAAccountAuthReq, ProtoOAAccountAuthRes, ProtoOASymbolsListReq, ProtoOASymbolsListRes,
    ProtoOASubscribeSpotsReq, ProtoOASubscribeSpotsRes, ProtoOASpotEvent, ProtoOAErrorRes,
)
from twisted.internet import reactor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
TICKDIR = os.path.join(DATA, "news_ticks")
SCHED = os.path.join(DATA, "news_schedule.json")
HEART = os.path.join(DATA, "news_recorder.heartbeat")
load_dotenv(os.path.join(ROOT, ".env"))
HOST = EndPoints.PROTOBUF_DEMO_HOST
assert HOST == "demo.ctraderapi.com", HOST
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY"]
PRE, POST, BASE_LEN = 10 * 60, 30 * 60, 40 * 60
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
FEED = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
EV = re.compile(r'\{"id":\d+,"ebaseId".*?"soloUrl":"[^"]*"\}')

st = {"acct": None, "sid2name": {}, "last": {}, "windows": [], "events": [], "n_today": 0, "last_spot": 0.0,
      "file": None, "file_day": None, "writer": None, "sched_ts": 0, "feed_ts": 0, "cur_window": None}


def log(msg):
    print(f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} [recorder] {msg}", flush=True)


def utc(ts):
    return datetime.fromtimestamp(ts, timezone.utc)


def market_closed(now=None):
    d = utc(now or time.time())
    return d.weekday() == 5 or (d.weekday() == 4 and d.hour >= 21) or (d.weekday() == 6 and d.hour < 21)


# ---------------------------------------------------------------- schedule
def http_get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def wanted(impact, cur, title):
    """high-impact USD/EUR, plus the medium-impact EUR flash PMIs (needed for the EU-PMI continuation study)."""
    return impact == "high" or (cur == "EUR" and "flash" in title.lower() and "pmi" in title.lower())


def fetch_feed():
    out = []
    for e in json.loads(http_get(FEED)):
        if e.get("country") not in ("USD", "EUR") or not wanted(e.get("impact", "").lower(), e["country"], e["title"]): continue
        try: t = int(datetime.fromisoformat(e["date"]).timestamp())
        except Exception: continue
        out.append(dict(t=t, cur=e["country"], title=e["title"], src="ff_json"))
    return out


def fetch_month(dt):
    tag = dt.strftime("%b").lower() + "." + str(dt.year)
    html = http_get(f"https://www.forexfactory.com/calendar?month={tag}").decode("cp1252", errors="replace")
    out = []
    for s in EV.findall(html):
        try: r = json.loads(s)
        except Exception: continue
        if r.get("currency") not in ("USD", "EUR") or not wanted(r.get("impactName"), r["currency"], r["name"]): continue
        if r.get("timeMasked") or r.get("timeLabel") in ("All Day", "Tentative"): continue
        out.append(dict(t=int(r["dateline"]), cur=r["currency"], title=r["name"], src="ff_month"))
    return out


def refresh_schedule(force=False):
    now = time.time(); evs = []
    cached = json.load(open(SCHED)) if os.path.exists(SCHED) else {"events": [], "month_ts": 0, "feed_ts": 0}
    month_ts, feed_ts = cached.get("month_ts", 0), cached.get("feed_ts", 0)
    old = cached.get("events", [])
    got_month = got_feed = None
    if force or now - month_ts > 86400:
        try:
            d = utc(now); got_month = fetch_month(d)
            if d.day >= 22:
                time.sleep(8); got_month += fetch_month((d.replace(day=1) + timedelta(days=32)).replace(day=1))
            month_ts = now; log(f"schedule: month page(s) -> {len(got_month)} target USD/EUR events")
        except Exception as e:
            month_ts = now - 86400 + 3600   # retry in 1h, never hammer
            log(f"schedule: month page fetch failed ({type(e).__name__}); keeping cached, retry in 1h")
    if force or now - feed_ts > 6 * 3600:
        try:
            time.sleep(2); got_feed = fetch_feed(); feed_ts = now
            log(f"schedule: weekly JSON feed -> {len(got_feed)} target USD/EUR events")
        except Exception as e:
            feed_ts = now - 6 * 3600 + 3600   # retry in 1h (the feed rate-limits repeated requests)
            log(f"schedule: JSON feed fetch failed ({type(e).__name__}); keeping cached, retry in 1h")
    evs = old if got_month is None else [e for e in old if e["src"] != "ff_month"] + got_month
    if got_feed is not None:
        evs = [e for e in evs if e["src"] != "ff_json"] + got_feed
    # de-duplicate (same time + currency + title); the feed and the month page agree on UTC times
    seen = {}; 
    for e in sorted(evs, key=lambda e: (e["t"], e["src"])):
        seen.setdefault((e["t"], e["cur"], e["title"].lower().replace("german ", "")), e)
    evs = sorted(seen.values(), key=lambda e: e["t"])
    evs = [e for e in evs if e["t"] > now - 3 * 86400]
    json.dump(dict(events=evs, month_ts=month_ts, feed_ts=feed_ts, updated=now), open(SCHED, "w"), indent=1)
    st["events"] = evs; st["windows"] = build_windows(evs)
    st["sched_ts"] = now


def build_windows(evs):
    news = []
    for e in evs:
        a, b = e["t"] - PRE, e["t"] + POST
        if news and a <= news[-1]["end"]:
            news[-1]["end"] = max(news[-1]["end"], b); news[-1]["events"].append(e)
        else:
            news.append(dict(kind="news", start=a, end=b, events=[e]))
    wins = list(news)
    day0 = utc(time.time() - 86400).date()
    for k in range(10):                    # baseline windows for the next days
        d = day0 + timedelta(days=k)
        if d.weekday() >= 5: continue
        rnd = random.Random(int(hashlib.md5(str(d).encode()).hexdigest()[:8], 16))
        for _ in range(50):
            s = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp()) + rnd.randint(3600, 19 * 3600)
            if all(s + BASE_LEN < w["start"] - 3600 or s > w["end"] + 3600 for w in news):
                wins.append(dict(kind="baseline", start=s, end=s + BASE_LEN, events=[])); break
    return sorted(wins, key=lambda w: w["start"])


def window_at(t):
    for w in st["windows"]:
        if w["start"] <= t < w["end"]: return w
    return None


def win_id(w):
    return f"{w['kind']}:{utc(w['start']):%Y%m%dT%H%MZ}"


# ---------------------------------------------------------------- writing
def writer_for(t):
    day = utc(t).strftime("%Y-%m-%d")
    if st["file_day"] != day:
        if st["file"]: st["file"].close()
        p = os.path.join(TICKDIR, f"{day}.csv"); new = not os.path.exists(p)
        st["file"] = open(p, "a", newline=""); st["writer"] = csv.writer(st["file"]); st["file_day"] = day
        if new: st["writer"].writerow(["recv_ts_ms", "server_ts_ms", "symbol", "bid", "ask", "window"])
    return st["writer"]


def note_window(w):
    p = os.path.join(TICKDIR, "windows.csv"); new = not os.path.exists(p)
    with open(p, "a", newline="") as f:
        wr = csv.writer(f)
        if new: wr.writerow(["window", "kind", "start_utc", "end_utc", "events"])
        wr.writerow([win_id(w), w["kind"], f"{utc(w['start']):%Y-%m-%d %H:%M}", f"{utc(w['end']):%Y-%m-%d %H:%M}",
                     " | ".join(f"{utc(e['t']):%H:%M} {e['cur']} {e['title']}" for e in w["events"])])


# ---------------------------------------------------------------- periodic
def tick_timer():
    now = time.time()
    if now - st["sched_ts"] > 6 * 3600:
        refresh_schedule()
    w = window_at(now)
    if w is not st["cur_window"]:
        if w is not None:
            log(f"window OPEN {win_id(w)} until {utc(w['end']):%H:%M}Z: " + "; ".join(e["title"] for e in w["events"]))
            note_window(w)
        elif st["cur_window"] is not None:
            log(f"window CLOSED {win_id(st['cur_window'])}; rows today {st['n_today']}")
        st["cur_window"] = w
    if st["file"]: st["file"].flush()
    if market_closed(now) or now - st["last_spot"] < 300:
        open(HEART, "w").write(str(int(now)))
    elif st["last_spot"] and now - st["last_spot"] > 600:
        log("no quotes for >10 min during market hours; exiting for a supervised restart"); stop(3); return
    reactor.callLater(5, tick_timer)


def status_timer():
    nxt = [w for w in st["windows"] if w["start"] > time.time()][:1]
    nx = f"{win_id(nxt[0])} ({utc(nxt[0]['start']) + timedelta(hours=8):%m-%d %H:%M} UB)" if nxt else "none"
    log(f"alive: last quote {time.time() - st['last_spot']:.0f}s ago, rows today {st['n_today']}, next window {nx}")
    reactor.callLater(1800, status_timer)


# ---------------------------------------------------------------- API
def stop(code=0):
    st["exit"] = code
    if st["file"]: st["file"].close(); st["file"] = None
    if reactor.running: reactor.stop()


def send(client, r):
    client.send(r, responseTimeoutInSeconds=30)


def on_msg(client, m):
    pt = m.payloadType
    if pt == ProtoOASpotEvent().payloadType:
        e = Protobuf.extract(m); name = st["sid2name"].get(e.symbolId)
        if not name: return
        now = time.time(); st["last_spot"] = now
        q = st["last"].setdefault(name, [None, None])
        if e.HasField("bid"): q[0] = e.bid / 1e5
        if e.HasField("ask"): q[1] = e.ask / 1e5
        w = st["cur_window"] if st["cur_window"] and st["cur_window"]["start"] <= now < st["cur_window"]["end"] else None
        if w is not None and q[0] is not None and q[1] is not None:
            writer_for(now).writerow([int(now * 1000), e.timestamp if e.HasField("timestamp") else "", name, q[0], q[1], win_id(w)])
            st["n_today"] += 1
        return
    if pt == ProtoOAErrorRes().payloadType:
        e = Protobuf.extract(m); log(f"API error {e.errorCode}: {e.description}"); return stop(2)
    if pt == ProtoOAApplicationAuthRes().payloadType:
        r = ProtoOAGetAccountListByAccessTokenReq(); r.accessToken = os.environ["CTRADER_ACCESS_TOKEN"]; send(client, r)
    elif pt == ProtoOAGetAccountListByAccessTokenRes().payloadType:
        demo = [a for a in Protobuf.extract(m).ctidTraderAccount if not a.isLive]
        if not demo: log("no demo account"); return stop(2)
        assert demo[0].isLive is False
        st["acct"] = demo[0].ctidTraderAccountId
        r = ProtoOAAccountAuthReq(); r.ctidTraderAccountId = st["acct"]; r.accessToken = os.environ["CTRADER_ACCESS_TOKEN"]
        send(client, r)
    elif pt == ProtoOAAccountAuthRes().payloadType:
        r = ProtoOASymbolsListReq(); r.ctidTraderAccountId = st["acct"]; send(client, r)
    elif pt == ProtoOASymbolsListRes().payloadType:
        ids = {s.symbolName: s.symbolId for s in Protobuf.extract(m).symbol}
        st["sid2name"] = {ids[s]: s for s in SYMBOLS if s in ids}
        r = ProtoOASubscribeSpotsReq(); r.ctidTraderAccountId = st["acct"]; r.subscribeToSpotTimestamp = True
        for sid in st["sid2name"]: r.symbolId.append(sid)
        send(client, r)
    elif pt == ProtoOASubscribeSpotsRes().payloadType:
        log(f"spot subscription OK: {sorted(st['sid2name'].values())} (demo account)")
        st["last_spot"] = time.time()


def main():
    for k in ("CTRADER_CLIENT_ID", "CTRADER_CLIENT_SECRET", "CTRADER_ACCESS_TOKEN"):
        if not os.environ.get(k): log(f"{k} missing"); sys.exit(1)
    os.makedirs(TICKDIR, exist_ok=True)
    refresh_schedule(force="--refresh" in sys.argv)
    up = [e for e in st["events"] if e["t"] > time.time()]
    log(f"schedule: {len(up)} upcoming high-impact USD/EUR releases, {len(st['windows'])} windows (incl. baseline)")
    if "--schedule-only" in sys.argv: return
    c = Client(HOST, EndPoints.PROTOBUF_PORT, TcpProtocol)
    c.setConnectedCallback(lambda cl: (log(f"connected to {HOST}"), cl.send(ProtoOAApplicationAuthReq(
        clientId=os.environ["CTRADER_CLIENT_ID"], clientSecret=os.environ["CTRADER_CLIENT_SECRET"]))))
    c.setDisconnectedCallback(lambda cl, reason: (log("disconnected; exiting for restart"), stop(4)))
    c.setMessageReceivedCallback(on_msg)
    c.startService()
    reactor.callLater(5, tick_timer); reactor.callLater(60, status_timer)
    reactor.run()
    sys.exit(st.get("exit", 0))


if __name__ == "__main__":
    main()
