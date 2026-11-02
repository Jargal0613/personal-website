"""Append-only JSONL journal helpers for the paper program (no broker code)."""
import fcntl
import json
import os
import time
from datetime import datetime, timezone

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "journal")
HYP = os.path.join(DIR, "hypotheses.jsonl")
DEC = os.path.join(DIR, "decisions.jsonl")
NEWS = os.path.join(DIR, "news.jsonl")
EQUITY = os.path.join(DIR, "equity.csv")
ASSUME = os.path.join(DIR, "assumptions.jsonl")


def now_iso(t=None):
    return datetime.fromtimestamp(time.time() if t is None else t, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _clean(o):
    if isinstance(o, float):
        return None if o != o or o in (float("inf"), float("-inf")) else round(o, 6)
    if isinstance(o, dict): return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_clean(v) for v in o]
    if hasattr(o, "item"): return _clean(o.item())
    return o


def append(path, rec):
    rec = dict(ts_utc=rec.pop("ts_utc", now_iso()), **rec)
    line = json.dumps(_clean(rec), separators=(",", ":"), default=str)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX); f.write(line + "\n"); fcntl.flock(f, fcntl.LOCK_UN)
    return rec


def read(path):
    if not os.path.exists(path): return []
    out = []
    with open(path) as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try: out.append(json.loads(ln))
                except json.JSONDecodeError: pass
    return out


def hyp_status():
    """latest status per hypothesis id (append-only log -> last record wins)."""
    st = {}
    for r in read(HYP):
        if r.get("type") in ("hypothesis", "status") and r.get("id"):
            cur = st.setdefault(r["id"], {})
            cur.update({k: v for k, v in r.items() if v is not None})
    return st
