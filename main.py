"""ONI Flush-Rider: a long/flat cbBTC bot for agent-fun/bars-replay/v1.

Strategy (1-minute bars, long only, at most one position):

- Sit in cash. The only entry signal is a genuine flush: when the close has
  fallen at least FLUSH_BPS over the last LOOKBACK bars (2 hours), capitulation
  is usually exhausted and a relief bounce follows. Buy SIZE_NUM/SIZE_DEN of
  the cash on hand. Ordinary chop never triggers an order, so the ~26 bps a
  full-size round trip costs in fees, slippage and impact is paid rarely.
- While holding, value the position against its own cost basis (fees
  included, as the harness reports it) and sell everything on the first of:
  take-profit at +TAKE_PROFIT_BPS, a hard stop at -STOP_BPS, a trailing stop
  TRAIL_BPS below the peak close once the gain has armed past
  TRAIL_ARM_BPS, or MAX_HOLD bars in the trade.
- After any exit, COOLDOWN bars must pass before the next entry, so a
  stop-out into a still-falling market cannot chain into repeated losses.
- Guardrails for the race bar (at least 1 trade, max drawdown <= 25%):
  entries stop near the end of the window (a late round trip cannot pay its
  costs), and if equity ever falls DD_HALT_BPS below its peak the bot
  flattens and stays flat.

Everything is a deterministic function of the bars and the account the
harness sends: no clock, no network, no randomness. The wire protocol is
spoken by the kit's Python SDK shim, vendored byte for byte under vendor/.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

LOOKBACK = 120          # bars in the flush measure (2 hours of 1-minute bars)
FLUSH_BPS = 130         # enter when the LOOKBACK return is at or below -FLUSH_BPS
TAKE_PROFIT_BPS = 120   # sell at this gain over the position's cost basis
TRAIL_ARM_BPS = 40      # trailing stop arms once the gain passes this
TRAIL_BPS = 45          # ... and fires this far below the peak close
STOP_BPS = 90           # hard stop below the cost basis
MAX_HOLD = 480          # bars; exit a position that has gone nowhere in 8 hours
COOLDOWN = 60           # bars between an exit and the next entry
SIZE_NUM, SIZE_DEN = 9, 10   # spend 90% of cash on an entry
MAX_SLIPPAGE_BPS = 100  # refuse a fill more than 1% past the deciding close
DD_HALT_BPS = 800       # flatten and halt if equity drops 8% under its peak
LATE_CUT = 1400         # no new entries at or after this scored bar

S = {
    "symbol": None,        # the universe's one symbol, from hello
    "closes": [],          # every close seen, in order
    "holding": False,      # a position was held at the last batch
    "entry_bar": 0,        # bar count when the current position first appeared
    "peak_close": 0,       # highest close since the position appeared
    "cooldown_until": 0,   # bar count before which no new entry is allowed
    "peak_equity": 0,      # highest equity seen, for the drawdown halt
    "halted": False,       # drawdown halt latched
}


def on_hello(state):
    S["symbol"] = next(iter(state.symbols))
    S["peak_equity"] = state.equity


def on_batch(state, batch):
    symbol = S["symbol"]
    close = state.close(symbol)
    if close is None:
        return []
    S["closes"].append(close)
    bar = len(S["closes"]) - 1  # index of this bar in the closes history

    if state.equity > S["peak_equity"]:
        S["peak_equity"] = state.equity

    holding = state.positions.get(symbol)
    orders = []

    if holding is not None and not S["holding"]:
        # The position first appears in the account: start its clocks.
        S["entry_bar"] = bar
        S["peak_close"] = close
    if holding is not None and close > S["peak_close"]:
        S["peak_close"] = close
    if holding is None and S["holding"]:
        # The position is gone (an exit filled): start the cooldown.
        S["cooldown_until"] = bar + COOLDOWN
    S["holding"] = holding is not None

    # Drawdown halt: flatten and never trade again this window.
    if S["peak_equity"] > 0 and state.equity * 10000 <= S["peak_equity"] * (10000 - DD_HALT_BPS):
        S["halted"] = True
    if S["halted"]:
        if holding is not None:
            orders.append({"side": "sell", "symbol": symbol, "qty": holding.qty,
                           "max_slippage_bps": MAX_SLIPPAGE_BPS})
        return orders

    if state.warming_up:
        return orders

    if holding is not None:
        value = state.value(symbol, holding.qty)
        gain_bps = (value * 10000 // holding.cost - 10000) if holding.cost > 0 else 0
        held = bar - S["entry_bar"]
        exit_now = (
            gain_bps >= TAKE_PROFIT_BPS
            or gain_bps <= -STOP_BPS
            or held >= MAX_HOLD
            or (gain_bps > TRAIL_ARM_BPS
                and close * 10000 < S["peak_close"] * (10000 - TRAIL_BPS))
        )
        if exit_now:
            orders.append({"side": "sell", "symbol": symbol, "qty": holding.qty,
                           "max_slippage_bps": MAX_SLIPPAGE_BPS})
        return orders

    # Flat: the only entry is a deep flush, early enough to pay its costs.
    scored = state.seq - state.warmup_bars
    if scored >= LATE_CUT or bar < LOOKBACK or bar < S["cooldown_until"]:
        return orders
    past = S["closes"][bar - LOOKBACK]
    if past > 0 and close * 10000 <= past * (10000 - FLUSH_BPS):
        spend = state.cash * SIZE_NUM // SIZE_DEN
        room = state.weight_room(symbol)
        if spend > room:
            spend = room
        if spend >= 1_000_000:  # the replay's 1 USDC minimum buy
            orders.append({"side": "buy", "symbol": symbol,
                           "notional_quote_units": spend,
                           "max_slippage_bps": MAX_SLIPPAGE_BPS})
    return orders


if __name__ == "__main__":
    makefun_bars.run(on_batch, on_hello=on_hello)
