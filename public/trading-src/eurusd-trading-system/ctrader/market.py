import time

from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAGetTrendbarsReq,
)


class MarketData:

    def __init__(self, max_candles=1500):

        # =====================================================
        # COMPLETED CANDLES
        # =====================================================

        self.candles = []

        self.max_candles = max_candles

        # =====================================================
        # LIVE PRICE
        # =====================================================

        self.current_bid = None
        self.current_ask = None
        self.last_price_timestamp = None

        # =====================================================
        # CURRENT M1 CANDLE
        # =====================================================

        self.current_candle = None
        self.candle_completed_callback = None

        # =========================================================
        # HISTORICAL / COMPLETED CANDLES
        # =========================================================

    def add_candle(self, candle):

        self.candles.append(candle)

        self._trim_candles()

    def add_candles(self, candles):

        if not candles:
            return

        # -----------------------------------------------------
        # If a live candle already exists, historical candles
        # must stay BEFORE the active candle.
        #
        # This prevents duplicate/overlapping candles.
        # -----------------------------------------------------

        if self.current_candle is not None:

            current_timestamp = (
                self.current_candle["timestamp"]
            )

            candles = [
                candle
                for candle in candles
                if candle["timestamp"]
                < current_timestamp
            ]

        self.candles = sorted(
            candles,
            key=lambda candle: candle["timestamp"]
        )

        self._trim_candles()

    def get_candles(self):

        return self.candles

    def get_recent_candles(self, count=50):

        if count <= 0:
            return []

        return self.candles[-count:]

    def get_latest_candle(self):

        if not self.candles:
            return None

        return self.candles[-1]

    def clear_candles(self):

        self.candles.clear()

    def _trim_candles(self):

        if len(self.candles) > self.max_candles:

            self.candles = (
                self.candles[-self.max_candles:]
            )

    # =========================================================
    # LIVE PRICE
    # =========================================================

    def update_price(
        self,
        bid=None,
        ask=None,
        timestamp=None,
    ):

        if bid is not None:

            self.current_bid = bid

        if ask is not None:

            self.current_ask = ask

        if timestamp is not None:

            self.last_price_timestamp = timestamp

        self._update_current_candle()

    def get_bid(self):

        return self.current_bid

    def get_ask(self):

        return self.current_ask

    def get_mid_price(self):

        if (
            self.current_bid is None
            or self.current_ask is None
        ):
            return None

        return round(
            (
                self.current_bid
                + self.current_ask
            ) / 2,
            6
        )

    def get_spread(self):

        if (
            self.current_bid is None
            or self.current_ask is None
        ):
            return None

        return round(
            self.current_ask
            - self.current_bid,
            6
        )

    # =========================================================
    # CURRENT M1 CANDLE
    # =========================================================

    def _update_current_candle(self):

        price = self.get_mid_price()

        timestamp = self.last_price_timestamp

        if price is None or timestamp is None:

            return

        # -----------------------------------------------------
        # cTrader timestamp is milliseconds.
        #
        # Convert it to the beginning of the M1 period.
        # -----------------------------------------------------

        candle_timestamp = (
            timestamp // 60000
        ) * 60

        # -----------------------------------------------------
        # CREATE FIRST LIVE CANDLE
        # -----------------------------------------------------

        if self.current_candle is None:

            self.current_candle = {

                "timestamp":
                    candle_timestamp,

                "open":
                    price,

                "high":
                    price,

                "low":
                    price,

                "close":
                    price,
            }

            return

        # -----------------------------------------------------
        # NEW MINUTE
        # -----------------------------------------------------

        if (
            candle_timestamp
            > self.current_candle["timestamp"]
        ):

            completed_candle = (
                self.current_candle.copy()
            )

            self.add_candle(
                completed_candle
            )
            if self.candle_completed_callback:
                self.candle_completed_callback()

            self.current_candle = {

                "timestamp":
                    candle_timestamp,

                "open":
                    price,

                "high":
                    price,

                "low":
                    price,

                "close":
                    price,
            }

            print(
                "\n🕐 M1 candle completed:"
            )

            print(
                completed_candle
            )

            print(
                "\n🕐 New M1 candle:"
            )

            print(
                self.current_candle
            )

            return

        # -----------------------------------------------------
        # UPDATE CURRENT CANDLE
        # -----------------------------------------------------

        if price > self.current_candle["high"]:

            self.current_candle["high"] = price

        if price < self.current_candle["low"]:

            self.current_candle["low"] = price

        self.current_candle["close"] = price

    def get_current_candle(self):

        return self.current_candle

    # =========================================================
    # TREND BAR PARSING
    # =========================================================

    def parse_trendbars(self, trendbars):

        candles = []

        for bar in trendbars:

            low = bar.low / 100000

            high = (
                bar.low
                + bar.deltaHigh
            ) / 100000

            open_price = (
                bar.low
                + bar.deltaOpen
            ) / 100000

            close = (
                bar.low
                + bar.deltaClose
            ) / 100000

            candle = {

                "timestamp":
                    bar.utcTimestampInMinutes * 60,

                "open":
                    open_price,

                "high":
                    high,

                "low":
                    low,

                "close":
                    close,
            }

            candles.append(candle)

        return candles



    # =========================================================
    # HISTORICAL DATA REQUEST
    # =========================================================

    def request_historical_candles(
        self,
        client,
        account_id,
        symbol_id,
        period=1,
        count=100,
        minutes=120,
        to_timestamp=None,
    ):
        if to_timestamp is None:
            to_timestamp = int(
                time.time() * 1000
            )

        from_time = (
            to_timestamp
            - (minutes * 60 * 1000)
        )

        request = ProtoOAGetTrendbarsReq()

        request.ctidTraderAccountId = (
            account_id
        )

        request.symbolId = symbol_id

        request.period = period

        request.fromTimestamp = (
            from_time
        )

        request.toTimestamp = (
            to_timestamp
        )

        request.count = count

        print(
            f"\nRequesting {count} "
            f"historical candles "
            f"(period={period})..."
        )

        print(
            f"From: {from_time}"
        )

        print(
            f"To:   {to_timestamp}"
        )

        client.send(
            request,
            responseTimeoutInSeconds=15
        )
