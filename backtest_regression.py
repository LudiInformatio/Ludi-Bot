import sqlite3
import pandas as pd
from datetime import datetime, timedelta

def backtest_regression_to_mean(lookback_days=60):
    """
    Backtest the regression-to-mean hypothesis over the last N days.
    
    Strategy:
    - For each player-game in the test period
    - Calculate season FG% (all prior games, min 10)
    - Calculate L5 FG% (prior 5 games)
    - If deviation > 15%, flag as BUY_LOW or SELL_HIGH
    - Track if N5 (next 5 games) regressed toward the mean
    
    Args:
        lookback_days: How many days back to test (default 60)
    """
    conn = sqlite3.connect('ludi.db')
    
    # Define test period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    print(f"\n{'='*70}")
    print(f"REGRESSION TO MEAN BACKTEST")
    print(f"{'='*70}")
    print(f"Test Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"{'='*70}\n")
    
    # Pull all games from this season
    query = '''
        SELECT player_name, game_date, fga, fgm, fg_pct, fg3a, fg3m, fg3_pct, pts
        FROM player_game_logs
        WHERE game_date >= '2024-10-01'
        ORDER BY player_name, game_date
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convert game_date to datetime
    df['game_date'] = pd.to_datetime(df['game_date'])
    
    print(f"📊 Total games in database: {len(df)}")
    print(f"📊 Unique players: {df['player_name'].nunique()}\n")
    
    results = []
    
    for player in df['player_name'].unique():
        player_data = df[df['player_name'] == player].reset_index(drop=True)
        
        # Need at least 15 games total (10 baseline + 5 L5)
        if len(player_data) < 15:
            continue
        
        # Iterate through games in the TEST PERIOD
        for i in range(len(player_data)):
            current_game_date = player_data.iloc[i]['game_date']
            
            # Skip if not in test period
            if current_game_date < start_date or current_game_date > end_date:
                continue
            
            # Need at least 10 prior games for season baseline
            if i < 10:
                continue
            
            # Need at least 5 games after for N5 validation
            if i + 5 > len(player_data):
                continue
            
            # Season avg (all games before current game, min 10)
            season_fgm = player_data.iloc[:i]['fgm'].sum()
            season_fga = player_data.iloc[:i]['fga'].sum()
            season_fg_pct = season_fgm / season_fga if season_fga > 50 else None  # Min 50 FGA
            
            if season_fg_pct is None:
                continue
            
            # L5 avg (5 games immediately before current)
            l5_fgm = player_data.iloc[max(0, i-5):i]['fgm'].sum()
            l5_fga = player_data.iloc[max(0, i-5):i]['fga'].sum()
            l5_fg_pct = l5_fgm / l5_fga if l5_fga > 10 else None  # Min 10 FGA
            
            if l5_fg_pct is None:
                continue
            
            # Calculate deviation
            deviation = (l5_fg_pct - season_fg_pct) / season_fg_pct
            
            # Flag signals (15% threshold)
            signal = None
            if deviation < -0.15:
                signal = 'BUY_LOW'
            elif deviation > 0.15:
                signal = 'SELL_HIGH'
            
            if signal:
                # N5 (next 5 games after current: i to i+4)
                n5_fgm = player_data.iloc[i:i+5]['fgm'].sum()
                n5_fga = player_data.iloc[i:i+5]['fga'].sum()
                n5_fg_pct = n5_fgm / n5_fga if n5_fga > 0 else None
                
                if n5_fg_pct is None:
                    continue
                
                # Did regression occur?
                regression_occurred = False
                if signal == 'BUY_LOW' and n5_fg_pct > l5_fg_pct:
                    regression_occurred = True
                elif signal == 'SELL_HIGH' and n5_fg_pct < l5_fg_pct:
                    regression_occurred = True
                
                # How close did N5 get to season mean?
                regression_strength = abs(n5_fg_pct - season_fg_pct) / abs(l5_fg_pct - season_fg_pct)
                
                results.append({
                    'player': player,
                    'game_date': current_game_date.strftime('%Y-%m-%d'),
                    'signal': signal,
                    'season_fg': round(season_fg_pct, 3),
                    'l5_fg': round(l5_fg_pct, 3),
                    'n5_fg': round(n5_fg_pct, 3),
                    'deviation': round(deviation * 100, 1),  # as percentage
                    'regression_occurred': regression_occurred,
                    'regression_strength': round(regression_strength, 2)
                })
    
    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    
    if len(results_df) == 0:
        print("⚠️  No regression signals found in the test period.")
        print("Try increasing lookback_days or lowering deviation threshold.\n")
        return None
    
    # Summary Statistics
    print(f"📈 BACKTEST RESULTS SUMMARY")
    print(f"{'='*70}\n")
    
    total_signals = len(results_df)
    buy_low_signals = results_df[results_df['signal'] == 'BUY_LOW']
    sell_high_signals = results_df[results_df['signal'] == 'SELL_HIGH']
    
    print(f"Total Regression Signals Flagged: {total_signals}\n")
    
    if len(buy_low_signals) > 0:
        buy_low_hit_rate = buy_low_signals['regression_occurred'].mean()
        buy_low_avg_improvement = buy_low_signals[buy_low_signals['regression_occurred']]['n5_fg'].mean() - buy_low_signals[buy_low_signals['regression_occurred']]['l5_fg'].mean()
        
        print(f"🔵 BUY_LOW Signals (Cold Shooters):")
        print(f"   Count: {len(buy_low_signals)}")
        print(f"   Regression Hit Rate: {buy_low_hit_rate:.1%}")
        print(f"   Avg FG% Improvement (when regression occurred): {buy_low_avg_improvement:+.1%}")
        print(f"   Top 3 Examples:")
        for _, row in buy_low_signals.nlargest(3, 'deviation').iterrows():
            print(f"     • {row['player']} on {row['game_date']}: L5={row['l5_fg']:.1%} → N5={row['n5_fg']:.1%}")
        print()
    
    if len(sell_high_signals) > 0:
        sell_high_hit_rate = sell_high_signals['regression_occurred'].mean()
        sell_high_avg_decline = sell_high_signals[sell_high_signals['regression_occurred']]['n5_fg'].mean() - sell_high_signals[sell_high_signals['regression_occurred']]['l5_fg'].mean()
        
        print(f"🔴 SELL_HIGH Signals (Hot Shooters):")
        print(f"   Count: {len(sell_high_signals)}")
        print(f"   Regression Hit Rate: {sell_high_hit_rate:.1%}")
        print(f"   Avg FG% Decline (when regression occurred): {sell_high_avg_decline:+.1%}")
        print(f"   Top 3 Examples:")
        for _, row in sell_high_signals.nlargest(3, 'deviation').iterrows():
            print(f"     • {row['player']} on {row['game_date']}: L5={row['l5_fg']:.1%} → N5={row['n5_fg']:.1%}")
        print()
    
    # Overall Assessment
    overall_hit_rate = results_df['regression_occurred'].mean()
    print(f"{'='*70}")
    print(f"📊 OVERALL REGRESSION HIT RATE: {overall_hit_rate:.1%}")
    
    if overall_hit_rate > 0.60:
        print(f"✅ STRONG SIGNAL — This is actionable alpha!")
    elif overall_hit_rate > 0.55:
        print(f"🟡 MODERATE SIGNAL — Worth incorporating with other factors")
    else:
        print(f"❌ WEAK SIGNAL — Not enough predictive power")
    print(f"{'='*70}\n")
    
    # Save detailed results
    output_file = f'regression_backtest_{lookback_days}d.csv'
    results_df.to_csv(output_file, index=False)
    print(f"💾 Detailed results saved to: {output_file}\n")
    
    return results_df


if __name__ == "__main__":
    # Run 60-day backtest
    results = backtest_regression_to_mean(lookback_days=60)
    
    # Also run 30-day and 90-day for comparison
    print("\n" + "="*70)
    print("RUNNING ADDITIONAL TIMEFRAMES FOR COMPARISON")
    print("="*70 + "\n")
    
    results_30d = backtest_regression_to_mean(lookback_days=30)
    results_90d = backtest_regression_to_mean(lookback_days=90)
