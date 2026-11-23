"""A patient, long-only CBBTC follower for the bars-replay race.

The idea is deliberately simple: own the asset from the first bar, and step aside
only when the last few hours of closes say the trend has genuinely turned.  A
wide exit band keeps quiet minutes from turning into costly round trips; the
fee, slippage and market impact of a full-size trade are roughly 26 bps, so a
signal has to be much bigger than the noise to be worth acting on.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
TREND_BARS = 240       # four hours of one-minute closes
ENTER_BPS = 5          # re-entry needs a close just above the trend line
EXIT_BPS = 120         # leave only on a real break below it
COOLDOWN_BARS = 30     # quiet bars before considering a re-entry
SLIP_BPS = 500         # headroom for modelled slippage plus our own impact
BPS = 10000


class Follower:
    """State kept between batches: only the closes we have actually been sent."""

    def __init__(self):
        self.closes = []
        self.total = 0          # running sum of the last TREND_BARS closes
        self.cooldown_until = 0  # seq before which a re-entry is not considered

    def trend(self):
        count = len(self.closes)
        if count == 0:
            return None
        return self.total // count

    def decide(self, state, batch):
        if state.warming_up:
            return []

        close = state.close(SYMBOL)
        if close is None:
            return []

        close = int(close)
        self.closes.append(close)
        self.total += close
        if len(self.closes) > TREND_BARS:
            self.total -= self.closes.pop(0)

        held = state.positions.get(SYMBOL)
        qty = held.qty if held is not None else 0

        # The first tradable bar establishes the position.  Later entries need
        # a close back above the trend line after a deliberate exit.
        if qty == 0:
            if state.seq <= 0 or len(self.closes) < 2:
                if state.cash > 0:
                    return [{
                        "side": "buy",
                        "symbol": SYMBOL,
                        "notional_quote_units": int(state.cash),
                        "max_slippage_bps": SLIP_BPS,
                    }]
                return []
            avg = self.trend()
            if (avg is not None and state.seq >= self.cooldown_until
                    and close * BPS > avg * (BPS + ENTER_BPS) and state.cash > 0):
                return [{
                    "side": "buy",
                    "symbol": SYMBOL,
                    "notional_quote_units": int(state.cash),
                    "max_slippage_bps": SLIP_BPS,
                }]
            return []

        avg = self.trend()
        if avg is not None and close * BPS < avg * (BPS - EXIT_BPS) and qty > 0:
            # An exit has to be paid for twice, so make a re-entry wait for a
            # short cooling-off period instead of chasing the first bounce.
            self.cooldown_until = state.seq + COOLDOWN_BARS
            return [{
                "side": "sell",
                "symbol": SYMBOL,
                "qty": int(qty),
                "max_slippage_bps": SLIP_BPS,
            }]
        return []


_follower = Follower()


def on_batch(state, batch):
    return _follower.decide(state, batch)


if __name__ == "__main__":
    makefun_bars.run(on_batch)
