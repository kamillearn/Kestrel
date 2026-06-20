"""
The Alpha Factory - Automated Edge Discovery.
Scans historical data, runs vectorized ORB backtests across global sessions, and ranks surviving edges.
"""
import os
import glob
import pandas as pd
import numpy as np
from pathlib import Path

# --- INSTITUTIONAL FILTER CRITERIA ---
MIN_TRADES = 100
MIN_WIN_RATE = 0.40  
MIN_T_STAT = 1.5     # Threshold for statistical significance

# --- SESSION TIMINGS (Eastern Time) ---
SESSIONS = [
    ("US Open", "09:30", "16:00"),
    ("EU Open", "03:00", "11:30"),  # 3:00 AM ET = 8:00 AM London / 9:00 AM Frankfurt
    ("Asia Open", "20:00", "02:30") # 8:00 PM ET = 9:00 AM Tokyo
]

def fast_orb_backtest(df: pd.DataFrame, start_time: str, end_time: str, or_minutes: int = 30) -> dict:
    """
    A lightning-fast approximation of Kestrel's ORB to screen assets quickly.
    Accounts for the OANDA bid-ask spread fetched in the CSV.
    """
    df = df.copy()
    
    # --- THE TIMEZONE FIX ---
    # Convert OANDA's UTC time to New York time
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC')
    df.index = df.index.tz_convert('America/New_York')
    
    # Isolate the specific global session
    try:
        df = df.between_time(start_time, end_time)
    except ValueError:
        return None
        
    df['date'] = df.index.date
    df['time'] = df.index.time
    
    trades = []
    
    for date, group in df.groupby('date'):
        # Skip days that are too short (early closures/holidays)
        if len(group) < or_minutes + 30: continue 
        
        # Approximate Opening Range
        opening_range = group.iloc[:or_minutes]
        or_high = opening_range['high'].max()
        or_low = opening_range['low'].min()
        
        session = group.iloc[or_minutes:]
        
        # Did we break out?
        long_break = session[session['high'] > or_high]
        short_break = session[session['low'] < or_low]
        
        # Get the average spread for the day to model realistic slippage
        avg_spread = group['spread'].mean() if 'spread' in group.columns else 0.0
        
        if not long_break.empty and (short_break.empty or long_break.index[0] < short_break.index[0]):
            # Long trade triggered (Buy at Ask, Sell at Bid -> pay the spread)
            entry_price = or_high + (avg_spread / 2)
            exit_price = session['close'].iloc[-1] - (avg_spread / 2)
            pnl = exit_price - entry_price
            trades.append(pnl)
            
        elif not short_break.empty:
            # Short trade triggered (Sell at Bid, Buy at Ask -> pay the spread)
            entry_price = or_low - (avg_spread / 2)
            exit_price = session['close'].iloc[-1] + (avg_spread / 2)
            pnl = entry_price - exit_price
            trades.append(pnl)

    if not trades:
        return None

    # Calculate Metrics
    trades_arr = np.array(trades)
    wins = trades_arr[trades_arr > 0]
    
    win_rate = len(wins) / len(trades_arr)
    avg_trade = np.mean(trades_arr)
    std_trade = np.std(trades_arr) if len(trades_arr) > 1 else 1.0
    t_stat = (avg_trade / std_trade) * np.sqrt(len(trades_arr)) if std_trade > 0 else 0
    profit_factor = abs(np.sum(wins) / np.sum(trades_arr[trades_arr < 0])) if np.sum(trades_arr[trades_arr < 0]) != 0 else 99.0
    
    return {
        "trades": len(trades_arr),
        "win_rate": win_rate,
        "expectancy": avg_trade,
        "profit_factor": profit_factor,
        "t_stat": t_stat
    }

def run_factory():
    print("🏭 Alpha Factory: Initiating Edge Discovery Sweep...")
    data_files = glob.glob("data/*.csv")
    
    if not data_files:
        print("No CSV files found in the data/ folder. Run fetch_oanda.py first!")
        return

    survivors = []
    
    for file in data_files:
        asset_name = Path(file).stem.replace("_M1", "")
        print(f"Scanning {asset_name}...")
        
        try:
            df = pd.read_csv(file, parse_dates=['time'], index_col='time')
            
            # Test ALL global sessions and keep EVERY session that passes the filter
            for session_name, start_t, end_t in SESSIONS:
                stats = fast_orb_backtest(df, start_t, end_t, or_minutes=30)
                
                if stats and stats['trades'] >= MIN_TRADES and stats['t_stat'] >= MIN_T_STAT:
                    stats['asset'] = asset_name
                    stats['session'] = session_name
                    survivors.append(stats)
                    
        except Exception as e:
            print(f"  [!] Error processing {asset_name}: {e}")

    # --- FILTER AND SORT THE SURVIVORS ---
    survivors = sorted(survivors, key=lambda x: x['t_stat'], reverse=True)

    # --- CONSOLE REPORT ---
    print("\n" + "="*85)
    print("🦅 ALPHA FACTORY SURVIVORS (T-Stat > 1.5)")
    print("="*85)
    if survivors:
        print(f"{'ASSET':<15} {'SESSION':<12} {'TRADES':<10} {'WIN %':<10} {'EXP (Pts)':<12} {'PF':<8} {'T-STAT':<8}")
        print("-" * 85)
        for s in survivors:
            print(f"{s['asset']:<15} {s['session']:<12} {s['trades']:<10} {s['win_rate']*100:>5.1f}%     {s['expectancy']:>8.2f}     {s['profit_factor']:>4.2f}    {s['t_stat']:>5.2f}")
    else:
        print("Sweep complete. No assets survived the institutional filter.")
    print("="*85)

if __name__ == "__main__":
    run_factory()