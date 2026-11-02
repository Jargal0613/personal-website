"""Read-only cTrader DEMO connection test.

Sends ONLY: ApplicationAuth, GetAccountListByAccessToken, AccountAuth,
TraderReq, SymbolsList, SymbolById, SubscribeSpots.  No trading requests.
Never prints credential values.
"""
import os
import sys
from collections import Counter

from dotenv import load_dotenv
from ctrader_open_api import Client, TcpProtocol, EndPoints, Protobuf
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq, ProtoOAApplicationAuthRes,
    ProtoOAGetAccountListByAccessTokenReq, ProtoOAGetAccountListByAccessTokenRes,
    ProtoOAAccountAuthReq, ProtoOAAccountAuthRes,
    ProtoOATraderReq, ProtoOATraderRes,
    ProtoOASymbolsListReq, ProtoOASymbolsListRes,
    ProtoOASymbolByIdReq, ProtoOASymbolByIdRes,
    ProtoOASubscribeSpotsReq, ProtoOASubscribeSpotsRes,
    ProtoOASpotEvent, ProtoOAErrorRes,
)
from twisted.internet import reactor

load_dotenv()
CID = os.getenv("CTRADER_CLIENT_ID")
SEC = os.getenv("CTRADER_CLIENT_SECRET")
TOK = os.getenv("CTRADER_ACCESS_TOKEN")
N_SPOTS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
HOST = EndPoints.PROTOBUF_DEMO_HOST
assert HOST == "demo.ctraderapi.com", HOST

state = {"acct": None, "sym": None, "spots": 0, "both": 0, "eq": 0,
         "bid": None, "ask": None, "ok": False}
spreads = Counter()


def stop(code=0):
    state["exit"] = code
    if reactor.running:
        reactor.stop()


def connected(client):
    print(f"Connected to {HOST}:{EndPoints.PROTOBUF_PORT}")
    r = ProtoOAApplicationAuthReq(); r.clientId = CID; r.clientSecret = SEC
    client.send(r)


def on_msg(client, m):
    pt = m.payloadType
    if pt == ProtoOAErrorRes().payloadType:
        e = Protobuf.extract(m)
        print(f"ERROR: {e.errorCode} {e.description}")
        return stop(2)
    if pt == ProtoOAApplicationAuthRes().payloadType:
        print("App auth: OK")
        r = ProtoOAGetAccountListByAccessTokenReq(); r.accessToken = TOK
        client.send(r)
    elif pt == ProtoOAGetAccountListByAccessTokenRes().payloadType:
        res = Protobuf.extract(m)
        print(f"Accounts on token: {len(res.ctidTraderAccount)}")
        for a in res.ctidTraderAccount:
            print(f"  ctidTraderAccountId={a.ctidTraderAccountId} traderLogin={a.traderLogin} "
                  f"isLive={a.isLive}")
        demo = [a for a in res.ctidTraderAccount if not a.isLive]
        if not demo:
            print("No demo account"); return stop(3)
        a = demo[0]
        assert a.isLive is False
        state["acct"] = a.ctidTraderAccountId
        print(f"Selected (first isLive==False, same rule as live_paper.py): {a.ctidTraderAccountId}")
        r = ProtoOAAccountAuthReq(); r.ctidTraderAccountId = a.ctidTraderAccountId; r.accessToken = TOK
        client.send(r)
    elif pt == ProtoOAAccountAuthRes().payloadType:
        print("Account auth: OK")
        r = ProtoOATraderReq(); r.ctidTraderAccountId = state["acct"]
        client.send(r)
    elif pt == ProtoOATraderRes().payloadType:
        t = Protobuf.extract(m).trader
        print(f"Trader: login={t.traderLogin} brokerName={t.brokerName} "
              f"accountType={t.accountType} accessRights={t.accessRights} isLimitedRisk={t.isLimitedRisk}")
        r = ProtoOASymbolsListReq(); r.ctidTraderAccountId = state["acct"]
        client.send(r, responseTimeoutInSeconds=15)
    elif pt == ProtoOASymbolsListRes().payloadType:
        res = Protobuf.extract(m)
        s = next((s for s in res.symbol if s.symbolName == "EURUSD"), None)
        state["sym"] = s.symbolId
        r = ProtoOASymbolByIdReq(); r.ctidTraderAccountId = state["acct"]; r.symbolId.append(s.symbolId)
        client.send(r, responseTimeoutInSeconds=15)
    elif pt == ProtoOASymbolByIdRes().payloadType:
        s = Protobuf.extract(m).symbol[0]
        print(f"EURUSD symbolId={s.symbolId} digits={s.digits} pipPosition={s.pipPosition} "
              f"commission={s.commission} commissionType={s.commissionType} "
              f"preciseTradingCommissionRate={s.preciseTradingCommissionRate}")
        r = ProtoOASubscribeSpotsReq(); r.ctidTraderAccountId = state["acct"]
        r.symbolId.append(state["sym"]); r.subscribeToSpotTimestamp = True
        client.send(r)
    elif pt == ProtoOASubscribeSpotsRes().payloadType:
        print("Spot subscription: OK; collecting quotes...")
    elif pt == ProtoOASpotEvent().payloadType:
        e = Protobuf.extract(m)
        if e.symbolId != state["sym"]:
            return
        state["spots"] += 1
        hb, ha = e.HasField("bid"), e.HasField("ask")
        if hb: state["bid"] = e.bid
        if ha: state["ask"] = e.ask
        if hb and ha:
            state["both"] += 1
        if state["bid"] is not None and state["ask"] is not None:
            sp = state["ask"] - state["bid"]
            spreads[sp] += 1
        if state["spots"] <= 5 or state["spots"] % 10 == 0:
            print(f"  spot #{state['spots']}: hasBid={hb} hasAsk={ha} bid={state['bid']/1e5 if state['bid'] else None} "
                  f"ask={state['ask']/1e5 if state['ask'] else None} ts={e.timestamp if e.HasField('timestamp') else None}")
        if state["spots"] >= N_SPOTS:
            state["ok"] = True
            print(f"Spots received: {state['spots']} (events carrying both bid&ask: {state['both']})")
            print("Spread distribution (raw points, 1 point = 0.00001 = 0.1 pip): "
                  + ", ".join(f"{k}:{v}" for k, v in sorted(spreads.items())))
            stop(0)


for n, v in [("CTRADER_CLIENT_ID", CID), ("CTRADER_CLIENT_SECRET", SEC), ("CTRADER_ACCESS_TOKEN", TOK)]:
    if not v:
        print(f"{n} missing"); sys.exit(1)

c = Client(HOST, EndPoints.PROTOBUF_PORT, TcpProtocol)
c.setConnectedCallback(connected)
c.setDisconnectedCallback(lambda cl, r: None)
c.setMessageReceivedCallback(on_msg)
c.startService()
reactor.callLater(120, lambda: (print("TIMEOUT"), stop(4)))
reactor.run()
sys.exit(state.get("exit", 1) if not state["ok"] else 0)
