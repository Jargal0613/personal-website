import csv
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from ctrader_open_api import (
    Client,
    TcpProtocol,
    EndPoints,
    Protobuf,
)

from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq,
    ProtoOAGetAccountListByAccessTokenReq,
    ProtoOAAccountAuthReq,
    ProtoOAAccountAuthRes,
    ProtoOAApplicationAuthRes,
    ProtoOAGetAccountListByAccessTokenRes,
    ProtoOASymbolsListReq,
    ProtoOASymbolsListRes,
    ProtoOASymbolByIdReq,
    ProtoOASymbolByIdRes,
    ProtoOASubscribeSpotsReq,
    ProtoOASubscribeSpotsRes,
    ProtoOASpotEvent,
    ProtoOAGetTrendbarsReq,
    ProtoOAGetTrendbarsRes,
)

from ctrader.market import MarketData

from twisted.internet import reactor


# ============================================================
# CONFIGURATION
# ============================================================

SYMBOL_NAME = "EURUSD"

RANGE_5M_THRESHOLD = 0.000326

INITIAL_EQUITY = 10.00

LOT_SIZE = 0.01

PIP_SIZE = 0.0001

PIP_VALUE_USD = 0.10

STOP_PIPS = 5.0

MAX_HOLD_MINUTES = 120

# Historical warm-up
WARMUP_CANDLES = 150

# Output
TRADE_FILE = "data/live_paper_trades.csv"
SIGNAL_FILE = "data/live_paper_signals.csv"


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")


# ============================================================
# MARKET DATA
# ============================================================

market_data = MarketData(
    max_candles=1500
)

selected_account_id = None
selected_symbol_id = None


# ============================================================
# PAPER ACCOUNT
# ============================================================

equity = INITIAL_EQUITY

position = None

trade_number = 0


# ============================================================
# SIGNAL STATE
# ============================================================

last_signal_timestamp = None


# ============================================================
# CSV INITIALIZATION
# ============================================================

def initialize_files():

    os.makedirs(
        "data",
        exist_ok=True
    )

    if not os.path.exists(SIGNAL_FILE):

        with open(
            SIGNAL_FILE,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "timestamp",
                "range_5m",
                "threshold",
                "bid",
                "ask",
                "spread",
                "signal",
            ])


    if not os.path.exists(TRADE_FILE):

        with open(
            TRADE_FILE,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "trade",
                "signal_time",
                "entry_time",
                "exit_time",
                "entry_price",
                "exit_price",
                "stop_price",
                "range_5m",
                "spread_entry",
                "exit_reason",
                "gross_pips",
                "net_pips",
                "pnl_usd",
                "equity",
                "mae_pips",
                "mfe_pips",
            ])


# ============================================================
# RESUME FROM TRADE LOG
# ============================================================

def resume_from_trade_log():
    """Continue trade numbering and equity from the existing trade log.

    Bookkeeping only (no strategy change). Uses the whole log rather than
    just the last row, so it stays correct even if an older run restarted
    numbering at #1: next trade = max(row count, highest trade #) + 1,
    equity = INITIAL_EQUITY + sum(pnl_usd).
    """

    global trade_number
    global equity

    try:
        with open(TRADE_FILE, newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
        if not rows:
            return
        trade_number = max(
            len(rows),
            max(int(row["trade"]) for row in rows),
        )
        equity = INITIAL_EQUITY + sum(
            float(row["pnl_usd"]) for row in rows
        )
        print(
            f"Resumed from {TRADE_FILE}: "
            f"{len(rows)} closed trades, "
            f"next trade #{trade_number + 1}, "
            f"equity ${equity:.3f}"
        )
    except Exception as error:
        trade_number = 0
        equity = INITIAL_EQUITY
        print(f"⚠️ Could not resume from trade log ({error}); starting fresh.")


# ============================================================
# HELPERS
# ============================================================

def timestamp_to_datetime(timestamp):

    return datetime.fromtimestamp(
        timestamp,
        timezone.utc,
    ).isoformat()


def calculate_range_5m():

    candles = market_data.get_candles()

    if len(candles) < 5:

        return None

    recent = candles[-5:]

    highest_high = max(
        candle["high"]
        for candle in recent
    )

    lowest_low = min(
        candle["low"]
        for candle in recent
    )

    return (
        highest_high -
        lowest_low
    )


# ============================================================
# SIGNAL LOGGING
# ============================================================

def save_signal(
    timestamp,
    range_5m,
    bid,
    ask,
    spread,
    signal,
):

    with open(
        SIGNAL_FILE,
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            timestamp_to_datetime(timestamp),
            range_5m,
            RANGE_5M_THRESHOLD,
            bid,
            ask,
            spread,
            signal,
        ])


# ============================================================
# TRADE LOGGING
# ============================================================

def save_trade(trade):

    with open(
        TRADE_FILE,
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            trade["trade"],
            timestamp_to_datetime(
                trade["signal_time"]
            ),
            timestamp_to_datetime(
                trade["entry_time"]
            ),
            timestamp_to_datetime(
                trade["exit_time"]
            ),
            trade["entry_price"],
            trade["exit_price"],
            trade["stop_price"],
            trade["range_5m"],
            trade["spread_entry"],
            trade["exit_reason"],
            trade["gross_pips"],
            trade["net_pips"],
            trade["pnl_usd"],
            trade["equity"],
            trade["mae_pips"],
            trade["mfe_pips"],
        ])


# ============================================================
# OPEN PAPER POSITION
# ============================================================

def open_paper_position(
    signal_candle,
    range_5m,
):

    global position
    global trade_number

    # --------------------------------------------------------
    # Only one position at a time
    # --------------------------------------------------------

    if position is not None:

        return

    entry_price = signal_candle["open"]

    entry_time = signal_candle["timestamp"]

    stop_price = (
        entry_price +
        STOP_PIPS * PIP_SIZE
    )

    trade_number += 1

    spread = market_data.get_spread()

    position = {

        "trade":
            trade_number,

        "signal_time":
            entry_time - 60,

        "entry_time":
            entry_time,

        "entry_price":
            entry_price,

        "stop_price":
            stop_price,

        "range_5m":
            range_5m,

        "spread_entry":
            spread,

        "mae_pips":
            0.0,

        "mfe_pips":
            0.0,
    }

    print()
    print("=" * 65)
    print("📉 PAPER SHORT OPENED")
    print("=" * 65)

    print(
        f"Trade:       #{trade_number}"
    )

    print(
        f"Entry time:  "
        f"{timestamp_to_datetime(entry_time)}"
    )

    print(
        f"Entry price: "
        f"{entry_price:.5f}"
    )

    print(
        f"Stop:        "
        f"{stop_price:.5f}"
    )

    print(
        f"Range 5M:    "
        f"{range_5m:.6f}"
    )

    print(
        f"Equity:      "
        f"${equity:.2f}"
    )

    print("=" * 65)


# ============================================================
# UPDATE PAPER POSITION
# ============================================================

def update_paper_position(candle):

    global position

    if position is None:

        return

    entry_price = position["entry_price"]

    stop_price = position["stop_price"]

    # --------------------------------------------------------
    # MAE
    #
    # Short position:
    # adverse movement = HIGH above entry
    # --------------------------------------------------------

    adverse_price = max(
        0,
        candle["high"] -
        entry_price,
    )

    mae_pips = (
        adverse_price /
        PIP_SIZE
    )

    position["mae_pips"] = max(
        position["mae_pips"],
        mae_pips,
    )

    # --------------------------------------------------------
    # MFE
    #
    # Short position:
    # favorable movement = entry - LOW
    # --------------------------------------------------------

    favorable_price = max(
        0,
        entry_price -
        candle["low"],
    )

    mfe_pips = (
        favorable_price /
        PIP_SIZE
    )

    position["mfe_pips"] = max(
        position["mfe_pips"],
        mfe_pips,
    )

    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    if candle["high"] >= stop_price:

        close_paper_position(
            candle,
            stop_price,
            "STOP",
        )

        return


    # --------------------------------------------------------
    # MAX HOLD
    # --------------------------------------------------------

    held_minutes = (
        candle["timestamp"] -
        position["entry_time"]
    ) // 60

    if held_minutes >= MAX_HOLD_MINUTES:

        close_paper_position(
            candle,
            candle["close"],
            "TIME",
        )


# ============================================================
# CLOSE PAPER POSITION
# ============================================================

def close_paper_position(
    candle,
    exit_price,
    reason,
):

    global position
    global equity

    if position is None:

        return

    entry_price = position["entry_price"]

    # --------------------------------------------------------
    # SHORT P&L
    # --------------------------------------------------------

    gross_pips = (
        entry_price -
        exit_price
    ) / PIP_SIZE

    spread = (
        position["spread_entry"]
        if position["spread_entry"] is not None
        else 0
    )

    spread_pips = (
        spread /
        PIP_SIZE
    )

    net_pips = (
        gross_pips -
        spread_pips
    )

    pnl_usd = (
        net_pips *
        PIP_VALUE_USD
    )

    equity += pnl_usd

    trade = {

        **position,

        "exit_time":
            candle["timestamp"],

        "exit_price":
            exit_price,

        "exit_reason":
            reason,

        "gross_pips":
            gross_pips,

        "net_pips":
            net_pips,

        "pnl_usd":
            pnl_usd,

        "equity":
            equity,

    }

    save_trade(trade)

    print()
    print("=" * 65)
    print("📊 PAPER SHORT CLOSED")
    print("=" * 65)

    print(
        f"Trade:       "
        f"#{position['trade']}"
    )

    print(
        f"Exit reason: "
        f"{reason}"
    )

    print(
        f"Entry:       "
        f"{entry_price:.5f}"
    )

    print(
        f"Exit:        "
        f"{exit_price:.5f}"
    )

    print(
        f"Gross:       "
        f"{gross_pips:+.2f} pips"
    )

    print(
        f"Net:         "
        f"{net_pips:+.2f} pips"
    )

    print(
        f"P&L:         "
        f"${pnl_usd:+.2f}"
    )

    print(
        f"MAE:         "
        f"{position['mae_pips']:.2f} pips"
    )

    print(
        f"MFE:         "
        f"{position['mfe_pips']:.2f} pips"
    )

    print(
        f"Equity:      "
        f"${equity:.2f}"
    )

    print("=" * 65)

    position = None


# ============================================================
# COMPLETED CANDLE
# ============================================================

def process_completed_candle():

    global last_signal_timestamp

    candles = market_data.get_candles()

    if len(candles) < 5:

        return

    completed = candles[-1]

    timestamp = completed["timestamp"]

    # --------------------------------------------------------
    # First update existing position
    # --------------------------------------------------------

    if position is not None:

        update_paper_position(
            completed
        )

        # If it closed, don't process this same candle
        # as a new entry signal.
        if position is None:

            return


    # --------------------------------------------------------
    # Prevent duplicate processing
    # --------------------------------------------------------

    if timestamp == last_signal_timestamp:

        return

    last_signal_timestamp = timestamp


    # --------------------------------------------------------
    # Calculate signal
    # --------------------------------------------------------

    range_5m = calculate_range_5m()

    if range_5m is None:

        return


    if range_5m > RANGE_5M_THRESHOLD:

        signal = "SHORT"

    else:

        signal = "NO_TRADE"


    bid = market_data.get_bid()

    ask = market_data.get_ask()

    spread = market_data.get_spread()


    # --------------------------------------------------------
    # Save signal
    # --------------------------------------------------------

    save_signal(
        timestamp,
        range_5m,
        bid,
        ask,
        spread,
        signal,
    )


    print()
    print("-" * 65)
    print("🧪 PAPER STRATEGY")
    print("-" * 65)

    print(
        f"Time:       "
        f"{timestamp_to_datetime(timestamp)}"
    )

    print(
        f"Range 5M:   "
        f"{range_5m:.6f}"
    )

    print(
        f"Threshold:  "
        f"{RANGE_5M_THRESHOLD:.6f}"
    )

    print(
        f"Signal:     "
        f"{signal}"
    )

    print(
        f"Equity:     "
        f"${equity:.2f}"
    )

    print("-" * 65)


    # --------------------------------------------------------
    # Signal means entry on NEXT candle OPEN.
    #
    # We don't have the next candle yet.
    # Therefore mark this signal and handle the entry
    # when the next candle completes.
    #
    # For now, we use a pending signal.
    # --------------------------------------------------------

    if (
        signal == "SHORT"
        and position is None
    ):

        global pending_signal

        pending_signal = {

            "signal_time":
                timestamp,

            "range_5m":
                range_5m,
        }


# ============================================================
# PENDING ENTRY
# ============================================================

pending_signal = None


def process_new_candle_for_entry():

    global pending_signal

    if pending_signal is None:

        return

    if position is not None:

        pending_signal = None

        return

    candles = market_data.get_candles()

    if len(candles) < 1:

        return

    candle = candles[-1]

    # --------------------------------------------------------
    # The candle immediately after signal candle is entry.
    # --------------------------------------------------------

    expected_entry_time = (
        pending_signal["signal_time"] +
        60
    )

    if candle["timestamp"] != expected_entry_time:

        return

    open_paper_position(
        candle,
        pending_signal["range_5m"],
    )

    pending_signal = None


# ============================================================
# COMBINED CALLBACK
# ============================================================

def candle_completed():

    # First process pending entry.
    process_new_candle_for_entry()

    # Then process existing position.
    if position is not None:

        update_paper_position(
            market_data.get_latest_candle()
        )

    # Finally generate new signal.
    process_completed_candle()


market_data.candle_completed_callback = (
    candle_completed
)


# ============================================================
# CONNECTION
# ============================================================

def connected(client):

    print(
        "Connected to cTrader."
    )

    request = (
        ProtoOAApplicationAuthReq()
    )

    request.clientId = CLIENT_ID

    request.clientSecret = CLIENT_SECRET

    client.send(request)


def disconnected(client, reason):

    print(
        f"Disconnected from cTrader: "
        f"{reason}"
    )


# ============================================================
# MESSAGE HANDLER
# ============================================================

def message_received(
    client,
    message,
):

    global selected_account_id
    global selected_symbol_id

    payload_type = message.payloadType


    # --------------------------------------------------------
    # APPLICATION AUTH
    # --------------------------------------------------------

    if payload_type == (
        ProtoOAApplicationAuthRes()
        .payloadType
    ):

        print(
            "✅ cTrader application authenticated."
        )

        request = (
            ProtoOAGetAccountListByAccessTokenReq()
        )

        request.accessToken = ACCESS_TOKEN

        client.send(request)

        return


    # --------------------------------------------------------
    # ACCOUNT LIST
    # --------------------------------------------------------

    if payload_type == (
        ProtoOAGetAccountListByAccessTokenRes()
        .payloadType
    ):

        response = Protobuf.extract(
            message
        )

        demo_accounts = [
            account
            for account
            in response.ctidTraderAccount
            if not account.isLive
        ]

        if not demo_accounts:

            print(
                "❌ No DEMO account found."
            )

            return

        selected_account_id = (
            demo_accounts[0]
            .ctidTraderAccountId
        )

        print(
            "Selected DEMO account."
        )

        request = (
            ProtoOAAccountAuthReq()
        )

        request.ctidTraderAccountId = (
            selected_account_id
        )

        request.accessToken = ACCESS_TOKEN

        client.send(request)

        return


    # --------------------------------------------------------
    # ACCOUNT AUTH
    # --------------------------------------------------------

    if payload_type == (
        ProtoOAAccountAuthRes()
        .payloadType
    ):

        print(
            "✅ DEMO account authenticated."
        )

        request = (
            ProtoOASymbolsListReq()
        )

        request.ctidTraderAccountId = (
            selected_account_id
        )

        client.send(request)

        return


    # --------------------------------------------------------
    # SYMBOL LIST
    # --------------------------------------------------------

    if payload_type == (
        ProtoOASymbolsListRes()
        .payloadType
    ):

        response = Protobuf.extract(
            message
        )

        eurusd = next(
            (
                symbol
                for symbol
                in response.symbol
                if symbol.symbolName
                == SYMBOL_NAME
            ),
            None,
        )

        if eurusd is None:

            print(
                "❌ EURUSD not found."
            )

            return

        selected_symbol_id = (
            eurusd.symbolId
        )

        print(
            f"EURUSD symbol ID: "
            f"{selected_symbol_id}"
        )

        request = (
            ProtoOASymbolByIdReq()
        )

        request.ctidTraderAccountId = (
            selected_account_id
        )

        request.symbolId.append(
            selected_symbol_id
        )

        client.send(request)

        return


    # --------------------------------------------------------
    # SYMBOL INFORMATION
    # --------------------------------------------------------

    if payload_type == (
        ProtoOASymbolByIdRes()
        .payloadType
    ):

        response = Protobuf.extract(
            message
        )

        symbol = response.symbol[0]

        selected_symbol_id = (
            symbol.symbolId
        )

        print()
        print(
            "EURUSD confirmed."
        )

        print(
            f"Symbol ID: "
            f"{selected_symbol_id}"
        )

        print(
            f"Digits: "
            f"{symbol.digits}"
        )

        print(
            f"Short selling: "
            f"{symbol.enableShortSelling}"
        )


        # ----------------------------------------------------
        # LIVE SPOT SUBSCRIPTION
        # ----------------------------------------------------

        request = (
            ProtoOASubscribeSpotsReq()
        )

        request.ctidTraderAccountId = (
            selected_account_id
        )

        request.symbolId.append(
            selected_symbol_id
        )

        request.subscribeToSpotTimestamp = True

        client.send(request)

        return


    # --------------------------------------------------------
    # SPOT SUBSCRIPTION
    # --------------------------------------------------------

    if payload_type == (
        ProtoOASubscribeSpotsRes()
        .payloadType
    ):

        print()
        print(
            "✅ EURUSD live subscription active."
        )

        print(
            "Waiting for M1 candles..."
        )

        return


    # --------------------------------------------------------
    # LIVE SPOT
    # --------------------------------------------------------

    if payload_type == (
        ProtoOASpotEvent()
        .payloadType
    ):

        response = Protobuf.extract(
            message
        )

        if (
            response.symbolId
            != selected_symbol_id
        ):

            return

        bid = None
        ask = None
        timestamp = None

        if response.HasField("bid"):

            bid = (
                response.bid /
                100000
            )

        if response.HasField("ask"):

            ask = (
                response.ask /
                100000
            )

        if response.HasField("timestamp"):

            timestamp = response.timestamp

        market_data.update_price(
            bid=bid,
            ask=ask,
            timestamp=timestamp,
        )


# ============================================================
# MAIN
# ============================================================

def main():

    initialize_files()

    resume_from_trade_log()

    print("=" * 65)
    print("VIRTUAL $10 PAPER TRADING ENGINE")
    print("=" * 65)

    print()
    print("⚠️ NO REAL ORDERS")
    print("⚠️ NO LIVE TRADING")
    print("⚠️ DEMO MARKET DATA ONLY")
    print()

    print(
        f"Initial equity: "
        f"${INITIAL_EQUITY:.2f}"
    )

    print(
        f"Position size: "
        f"{LOT_SIZE:.2f} lot"
    )

    print(
        f"Stop: "
        f"{STOP_PIPS:.1f} pips"
    )

    print(
        f"Max hold: "
        f"{MAX_HOLD_MINUTES} minutes"
    )

    print(
        f"Strategy threshold: "
        f"{RANGE_5M_THRESHOLD}"
    )

    print()

    if not CLIENT_ID:
        raise ValueError(
            "CTRADER_CLIENT_ID missing."
        )

    if not CLIENT_SECRET:
        raise ValueError(
            "CTRADER_CLIENT_SECRET missing."
        )

    if not ACCESS_TOKEN:
        raise ValueError(
            "CTRADER_ACCESS_TOKEN missing."
        )

    client = Client(
        EndPoints.PROTOBUF_DEMO_HOST,
        EndPoints.PROTOBUF_PORT,
        TcpProtocol,
    )

    client.setConnectedCallback(
        connected
    )

    client.setDisconnectedCallback(
        disconnected
    )

    client.setMessageReceivedCallback(
        message_received
    )

    client.startService()

    reactor.run()


if __name__ == "__main__":

    main()
