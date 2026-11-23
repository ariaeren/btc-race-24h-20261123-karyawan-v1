# Patient CBBTC Follower

A long-only trading bot for the `btc-race-24h-20261123-0511` bars replay.

It buys CBBTC on the first tradable bar and keeps it while the four-hour average
of closes supports the move. It only steps aside when price breaks a wide 120 bp
band below that average, and then waits 30 bars before it will buy again. The
wide band exists because a full-size round trip costs about 26 bps: reacting to
every little wiggle would donate that cost to the pool.

All decisions use integer quote units and the closes sent in the batches. No
clock, no environment, no network, no randomness. The Python protocol shim in
`vendor/` is a byte-for-byte copy of the kit's SDK.

Run locally with the kit's grade command (a Docker-capable host is required for
the Python runtime).
