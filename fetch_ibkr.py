"""
fetch_ibkr.py — pull 1-MINUTE intraday history for an equity-index basket from
IBKR and stitch a front-month continuous series, for the ORB cross-market test.

WHY THIS REWRITE (error 10339):
  IBKR does NOT allow endDateTime on a CONTINUOUS future (ContFuture), so you
  cannot page backward for deep intraday history with it — you get one window
  ending 'now' and that's it. The fix: request the INDIVIDUAL DATED contracts
  (regular Future, where endDateTime paging IS allowed), page each one back, then
  stitch them front-month into a continuous 1-min series.

  ORB is self-contained per session (flat by the close, no prior-day levels), so
  simple front-month stitching with a fixed roll is plenty accurate here.

OUTPUT:
  {SYMBOL}_M1.csv  columns: time,open,high,low,close,volume,spread  (naive UTC) —
  the exact schema Daybreak's loader/backtester/validate.py expect.

SESSION WARNING:
  ORB keys off a market's CASH OPEN. NQ/ES/RTY open 09:30 ET (Daybreak default).
  DAX opens 09:00 Europe/Berlin; the Nikkei opens 09:00 Asia/Tokyo — those need a
  Session at the local open + the CSV localised to that tz (see footer notes).

Requires TWS / IB Gateway (API enabled) and the relevant market-data + historical
subscriptions. Empty output => missing subscription, not a code bug.

    pip install ib-async pandas
"""
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from ib_async import IB, Future, util

# ---- connection -------------------------------------------------------------
HOST, PORT, CID = "127.0.0.1", 7497, 21          # 7497 paper / 7496 live

# ---- request settings -------------------------------------------------------
BARSIZE        = "1 min"
WHATSHOW       = "TRADES"
USE_RTH        = False
LOOKBACK_DAYS  = 1500                            # ~4 years
CHUNK          = "2 W"                           # per-request window for 1-min (dated future)
ROLL_BDAYS     = 5                               # roll this many business days before expiry
SLEEP_SEC      = 11                              # pacing: <60 hist requests / 10 min
MAX_CHUNKS     = 60                              # safety cap per contract window
OUT_DIR        = "."

# symbol, exchange, currency, cash-open(local), tz
BASKET = [
    # The European Session
    #("ESTX50", "EUREX", "EUR", "09:00", "Europe/Berlin"),    # Euro Stoxx 50
    ("Z",      "ICEEU", "GBP", "08:00", "Europe/London"),    # UK FTSE 100

    # The Asian Session
    ("HSI",    "HKFE",  "HKD", "09:15", "Asia/Hong_Kong"),   # Hang Seng Index
    ("AP",     "SNFE",  "AUD", "09:50", "Australia/Sydney"), # ASX SPI 200
]


def _naive_utc(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True).dt.tz_convert("UTC").dt.tz_localize(None)


def ensure_connected(ib):
    if not ib.isConnected():
        print("   reconnecting …")
        ib.connect(HOST, PORT, clientId=CID, timeout=15)
        time.sleep(1)


def safe_hist(ib, contract, end, dur, what=WHATSHOW):
    """reqHistoricalData with pacing back-off and reconnect on socket drop."""
    for attempt in range(4):
        try:
            ensure_connected(ib)
            return ib.reqHistoricalData(
                contract, endDateTime=end, durationStr=dur, barSizeSetting=BARSIZE,
                whatToShow=what, useRTH=USE_RTH, formatDate=2)
        except Exception as e:
            msg = str(e).lower()
            if any(k in msg for k in ("pacing", "162", "166")):
                print(f"   pacing; backing off 30s …"); time.sleep(30)
            elif "disconnect" in msg or "socket" in msg or "reset" in msg:
                print(f"   socket dropped; retry {attempt+1}/4"); time.sleep(5)
            else:
                print(f"   hist error: {e}"); return []
    return []


def list_dated_contracts(ib, symbol, exchange, currency):
    """All (incl. expired) dated contracts, ascending by expiry."""
    cds = ib.reqContractDetails(
        Future(symbol=symbol, exchange=exchange, currency=currency, includeExpired=True))
    cons = [cd.contract for cd in cds]
    cons.sort(key=lambda c: c.lastTradeDateOrContractMonth)
    return cons


def fetch_window(ib, contract, start_dt, end_dt):
    """Page a single dated contract backward over [start_dt, end_dt]."""
    frames, cursor, earliest = [], end_dt, None
    for _ in range(MAX_CHUNKS):
        bars = safe_hist(ib, contract, cursor, CHUNK)
        if not bars:
            break
        df = util.df(bars)
        frames.append(df)
        first = pd.to_datetime(df["date"].iloc[0], utc=True)
        if earliest is not None and first >= earliest:    # not advancing -> done
            break
        earliest = first
        if first <= start_dt:
            break
        cursor = bars[0].date
        time.sleep(SLEEP_SEC)
    if not frames:
        return None
    out = pd.concat(frames, ignore_index=True)
    out["t"] = pd.to_datetime(out["date"], utc=True)
    out = out[(out["t"] >= start_dt) & (out["t"] <= end_dt)]
    return out


def fetch_symbol(ib, symbol, exchange, currency):
    now = datetime.now(timezone.utc)
    target_start = now - timedelta(days=LOOKBACK_DAYS)
    cons = list_dated_contracts(ib, symbol, exchange, currency)
    if not cons:
        print(f"   ! no contract chain for {symbol} ({exchange})"); return None

    # roll date per contract = lastTrade - ROLL_BDAYS business days
    def roll(c):
        lt = pd.to_datetime(c.lastTradeDateOrContractMonth[:8], format="%Y%m%d", utc=True)
        return lt - pd.tseries.offsets.BDay(ROLL_BDAYS)

    rolls = [roll(c) for c in cons]
    frames = []
    for i, c in enumerate(cons):
        win_end = min(rolls[i], pd.Timestamp(now))
        win_start = rolls[i - 1] if i > 0 else (win_end - pd.Timedelta(days=100))
        win_end = min(win_end, pd.Timestamp(now))
        if win_end <= pd.Timestamp(target_start):      # window entirely too old
            continue
        win_start = max(win_start, pd.Timestamp(target_start))
        if win_start >= win_end:
            continue
        print(f"   {c.localSymbol or symbol}: {win_start:%Y-%m-%d} .. {win_end:%Y-%m-%d}")
        w = fetch_window(ib, c, win_start, win_end)
        if w is not None and len(w):
            frames.append(w)
    if not frames:
        return None
    out = pd.concat(frames, ignore_index=True)
    out["time"] = _naive_utc(out["t"])
    out = (out[["time", "open", "high", "low", "close", "volume"]]
           .drop_duplicates(subset="time").sort_values("time").reset_index(drop=True))
    return out, cons[-1]      # also return the active (front) contract for the spread sample


def estimate_spread(ib, contract) -> float:
    bars = safe_hist(ib, contract, "", "2 D", what="BID_ASK")
    if not bars:
        return 0.0
    df = util.df(bars)
    return float((df["high"] - df["low"]).clip(lower=0).median())


def main():
    ib = IB()
    ib.connect(HOST, PORT, clientId=CID, timeout=15)
    ok, miss = [], []
    for symbol, exchange, currency, open_local, tz in BASKET:
        print(f"[{symbol:3} {exchange:5}] 1-min history (open {open_local} {tz}) …")
        try:
            res = fetch_symbol(ib, symbol, exchange, currency)
        except Exception as e:
            print(f"   ! {symbol} failed: {e}"); miss.append(symbol); continue
        if not res or res[0] is None or res[0].empty:
            print(f"   ! {symbol} no data (check {exchange} subscription)."); miss.append(symbol)
            time.sleep(SLEEP_SEC); continue
        df, front = res
        spread = estimate_spread(ib, front)
        df["spread"] = spread
        path = f"{OUT_DIR}/{symbol}_M1.csv"
        df.to_csv(path, index=False)
        print(f"   saved {len(df):,} bars ({df['time'].iloc[0]} .. {df['time'].iloc[-1]}) "
              f"spread≈{spread:g} -> {path}")
        ok.append(symbol)
        time.sleep(SLEEP_SEC)
    ib.disconnect()
    print(f"\nDone. Got {len(ok)}: {ok}")
    if miss:
        print(f"Missing (likely subscription): {miss}")


if __name__ == "__main__":
    main()

# -----------------------------------------------------------------------------
# SESSIONS — NQ/ES/RTY use Daybreak's default 09:30 ET session and drop straight
# into:  python scripts/validate.py NQ=NQ_M1.csv ES=ES_M1.csv RTY=RTY_M1.csv
#
# DAX/NKD open at a different LOCAL time, so the opening range must be measured
# from that market's tz, not UTC->ET. Until the loader is generalised, localise
# those CSVs to the market tz and anchor the OR to 09:00 local:
#   Europe/Berlin (DAX), Asia/Tokyo (NKD).  Running them on the 09:30-ET clock is
#   meaningless. Ask Daybreak to add per-market Sessions + a tz-aware loader.
# -----------------------------------------------------------------------------