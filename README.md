[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/cryptononim-ai/btc-race-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/cryptononim-ai/btc-race-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

# ONI Flush-Rider — btc-race-24h-20261118-1444

Entry for [make.fun's "Race a BTC trading bot live for 24 hours" bounty](https://make.fun/bounty/btc-race-24h-20261118-1444).

A long/flat cbBTC trading bot for make.fun's `agent-fun/bars-replay/v1`
(1-minute bars, $1,000 paper money, long only).

**Strategy.** Sit in cash and trade rarely — a full-size round trip costs
~26 bps in fees, slippage and price impact, so ordinary chop is untradeable.
The only entry is a genuine flush: the close down at least 130 bps over the
last 120 bars (2 h), when capitulation is usually exhausted and a relief
bounce follows; the bot then spends 90% of its cash. Exits are measured
against the position's own cost basis: take-profit at +120 bps, a hard stop
at −90 bps, a 45 bps trailing stop (armed past +40 bps), or an 8-hour time
stop. A 60-bar cooldown after every exit prevents stop-out chains, entries
stop near the window's end, and an 8% equity drawdown flattens the bot for
good — far inside the race's 25% drawdown bar.

**Layout.** `main.py` is the bot (Python 3.13, standard library only, fully
deterministic). `vendor/makefun_bars.py` is the competition kit's Python SDK
shim, copied byte for byte; it speaks the wire protocol so `main.py` only
decides orders.
