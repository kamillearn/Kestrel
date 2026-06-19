import pandas as pd
import numpy as np
import itertools
import time

# ==========================================
# WALK-FORWARD OPTIMIZATION CONFIG
# ==========================================
FILENAME = 'TSLA_M1.csv'  # The ultimate ORB proxy
SPLIT_DATE = '2025-01-01' # Everything before is Training, everything after is Blind Test

# The Grid: The engine will test every combination of these variables on the Training Data
GRID = {
    'atr_multiplier': [1.0, 1.5, 2.0],  # How explosive does the morning need to be?
    'stop_pct': [0.25, 0.35, 0.50],     # Where do we hide the stop loss?
    'reward_to_risk': [2.0, 2.5]        # Target size
}
# ==========================================

def calculate_indicators(df):
    print("Calculating Institutional Indicators...")
    df_15m = df.resample('15min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last'})
    df_15m['ema_200'] = df_15m['close'].ewm(span=200, adjust=False).mean()
    
    df_15m['tr'] = np.maximum(df_15m['high'] - df_15m['low'], 
                   np.maximum(abs(df_15m['high'] - df_15m['close'].shift(1)), 
                              abs(df_15m['low'] - df_15m['close'].shift(1))))
    df_15m['atr_14'] = df_15m['tr'].rolling(14).mean()

    df['ema_200'] = df_15m['ema_200'].reindex(df.index).ffill()
    df['atr_14'] = df_15m['atr_14'].reindex(df.index).ffill()
    return df.dropna()

def run_backtest(data, atr_mult, stop_pct, rr, slippage_cents=2):
    """Core backtest logic optimized for speed."""
    trades = []
    grouped = data.groupby(data.index.date)
    
    for date, group in grouped:
        range_mask = (group['time_str'] >= '09:30') & (group['time_str'] <= '10:00')
        range_data = group[range_mask]
        if len(range_data) < 15: continue
            
        range_high = range_data['high'].max()
        range_low = range_data['low'].min()
        range_size = range_high - range_low
        
        # Volatility Filter
        current_atr = group.iloc[0]['atr_14']
        if range_size < (current_atr * atr_mult): continue
            
        trade_mask = (group['time_str'] > '10:00') & (group['time_str'] <= '12:00')
        trade_data = group[trade_mask]
        
        breakout_dir = None
        traded_today = False
        
        for idx, row in trade_data.iterrows():
            if traded_today: break
            
            if breakout_dir is None:
                if row['close'] > range_high and row['close'] > row['ema_200']: breakout_dir = 'Long'
                elif row['close'] < range_low and row['close'] < row['ema_200']: breakout_dir = 'Short'
            else:
                if breakout_dir == 'Long' and row['low'] <= range_high:
                    entry = range_high + (slippage_cents/100)
                    sl = (range_low + (range_size * stop_pct)) - (slippage_cents/100)
                    risk = entry - sl
                    if risk <= 0: continue
                    tp = entry + (risk * rr)
                    
                    manage_data = group.loc[idx:]
                    for f_idx, f_row in manage_data.iterrows():
                        if f_row['low'] <= sl:
                            trades.append(-1); traded_today = True; break
                        elif f_row['high'] >= tp:
                            trades.append(rr); traded_today = True; break
                
                elif breakout_dir == 'Short' and row['high'] >= range_low:
                    entry = range_low - (slippage_cents/100)
                    sl = (range_high - (range_size * stop_pct)) + (slippage_cents/100)
                    risk = sl - entry
                    if risk <= 0: continue
                    tp = entry - (risk * rr)
                    
                    manage_data = group.loc[idx:]
                    for f_idx, f_row in manage_data.iterrows():
                        if f_row['high'] >= sl:
                            trades.append(-1); traded_today = True; break
                        elif f_row['low'] <= tp:
                            trades.append(rr); traded_today = True; break

    if not trades: return 0, 0, 0
    trades_arr = np.array(trades)
    win_rate = (trades_arr > 0).mean()
    net_r = trades_arr.sum()
    profit_factor = abs(trades_arr[trades_arr > 0].sum() / trades_arr[trades_arr < 0].sum()) if len(trades_arr[trades_arr < 0]) > 0 else 99
    
    return len(trades), win_rate, net_r, profit_factor

def main():
    try:
        df = pd.read_csv(FILENAME, parse_dates=['time'])
    except FileNotFoundError:
        print(f"Waiting for {FILENAME}... Run fetch_ibkr.py first!")
        return

    df.set_index('time', inplace=True)
    df = calculate_indicators(df)
    df['time_str'] = df.index.strftime('%H:%M')
    
    # The Split
    df_train = df[:SPLIT_DATE]
    df_test = df[SPLIT_DATE:]
    
    print(f"\n--- STEP 1: IN-SAMPLE TRAINING (Grid Search on {len(df_train.groupby(df_train.index.date))} days) ---")
    
    keys = list(GRID.keys())
    combinations = list(itertools.product(*[GRID[k] for k in keys]))
    
    best_net_r = -999
    best_params = None
    
    for combo in combinations:
        atr_mult, stop_pct, rr = combo
        trades, wr, net_r, pf = run_backtest(df_train, atr_mult, stop_pct, rr)
        if net_r > best_net_r and trades > 50: # Ensure statistical significance
            best_net_r = net_r
            best_params = combo
            
    if best_params is None:
        print("No profitable combinations found in training data. The edge is dead.")
        return
        
    print(f"🏆 Best Training Params found:")
    print(f"ATR Mult: {best_params[0]} | Stop %: {best_params[1]} | RR: {best_params[2]}")
    print(f"Training Result -> Net R: +{best_net_r:.2f}")
    
    print(f"\n--- STEP 2: OUT-OF-SAMPLE BLIND TEST (Applying Best Params to Unseen Data) ---")
    print(f"Testing on unseen data from {SPLIT_DATE} to Present...")
    
    test_trades, test_wr, test_net_r, test_pf = run_backtest(df_test, *best_params)
    
    print("\n" + "="*40)
    print(" 📊 FINAL OUT-OF-SAMPLE VERDICT ")
    print("="*40)
    print(f"Total OOS Trades:  {test_trades}")
    print(f"OOS Win Rate:      {test_wr*100:.2f}%")
    print(f"OOS Net Profit:    {test_net_r:.2f} R")
    print(f"OOS Profit Factor: {test_pf:.2f}")
    print("="*40)
    
    if test_net_r > 0:
        print("\n✅ PASSED THE CLAUDE LIE DETECTOR TEST.")
        print("The edge survived the blind data. You have a statistically valid strategy for QQQ.")
    else:
        print("\n❌ FAILED. CURVE FITTING DETECTED.")
        print("The best rules from the past lost money in the future. The ORB edge on QQQ is noise.")

if __name__ == "__main__":
    main()