import sqlite3
import pandas as pd
from datetime import datetime, timedelta

def backtest_with_filters(lookback_days=60):
    """
    Enhanced regression backtest with injury/minutes filters.
    
    Filters applied:
    1. Minutes stability: L5 minutes within 20% of season average
    2. Minimum volume: Season average >= 15 MPG
    3. Exclude extreme outliers: Players with <50 total FGA in season
    """
    conn = sqlite3.connect('ludi.db')
    
    # Define test period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    print(f"\n{'='*70}")
    print(f"FILTERED REGRESSION BACKTEST (Injury/Minutes Logic)")
    print(f"{'='*70}")
    print(f"Test Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"{'='*70}\n")
    
    # Pull all games with minutes data
    query = '''
        SELECT player_name, game_date, fga, fgm, fg_pct, minutes, pts
        FROM player_game_logs
        WHERE game_date >= '2024-10-01'
        ORDER BY player_name, game_date
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    df['game_date'] = pd.to_datetime(df['game_date'])
    
    print(f"📊 Total games in database: {len(df)}")
    print(f"📊 Unique players: {df['player_name'].nunique()}\n")
    
    results_base = []  # Unfiltered (baseline)
    results_filtered = []  # With filters
    
    for player in df['player_name'].unique():
        player_data = df[df['player_name'] == player].reset_index(drop=True)
        
        if len(player_data) < 15:
            continue
        
        for i in range(len(player_data)):
            current_game_date = player_data.iloc[i]['game_date']
            
            if current_game_date < start_date or current_game_date > end_date:
                continue
            
            if i < 10 or i + 5 > len(player_data):
                continue
            
            # Season stats
            season_fgm = player_data.iloc[:i]['fgm'].sum()
            season_fga = player_data.iloc[:i]['fga'].sum()
            season_fg_pct = season_fgm / season_fga if season_fga > 50 else None
            season_min = player_data.iloc[:i]['minutes'].mean()
            
            if season_fg_pct is None or season_min < 5:
                continue
            
            # L5 stats
            l5_fgm = player_data.iloc[max(0, i-5):i]['fgm'].sum()
            l5_fga = player_data.iloc[max(0, i-5):i]['fga'].sum()
            l5_fg_pct = l5_fgm / l5_fga if l5_fga > 10 else None
            l5_min = player_data.iloc[max(0, i-5):i]['minutes'].mean()
            
            if l5_fg_pct is None:
                continue
            
            # Calculate deviation
            deviation = (l5_fg_pct - season_fg_pct) / season_fg_pct
            
            # Flag signals
            signal = None
            if deviation < -0.15:
                signal = 'BUY_LOW'
            elif deviation > 0.15:
                signal = 'SELL_HIGH'
            
            if signal:
                # N5 stats
                n5_fgm = player_data.iloc[i:i+5]['fgm'].sum()
                n5_fga = player_data.iloc[i:i+5]['fga'].sum()
                n5_fg_pct = n5_fgm / n5_fga if n5_fga > 0 else None
                
                if n5_fg_pct is None:
                    continue
                
                # Check regression
                regression_occurred = False
                if signal == 'BUY_LOW' and n5_fg_pct > l5_fg_pct:
                    regression_occurred = True
                elif signal == 'SELL_HIGH' and n5_fg_pct < l5_fg_pct:
                    regression_occurred = True
                
                # Base result (no filters)
                base_record = {
                    'player': player,
                    'game_date': current_game_date.strftime('%Y-%m-%d'),
                    'signal': signal,
                    'season_fg': round(season_fg_pct, 3),
                    'season_min': round(season_min, 1),
                    'l5_fg': round(l5_fg_pct, 3),
                    'l5_min': round(l5_min, 1),
                    'n5_fg': round(n5_fg_pct, 3),
                    'deviation': round(deviation * 100, 1),
                    'regression_occurred': regression_occurred,
                    'filter_status': 'UNFILTERED'
                }
                results_base.append(base_record)
                
                # Apply filters
                minutes_stable = abs(l5_min - season_min) / season_min < 0.20 if season_min > 0 else False
                min_volume = season_min >= 15.0
                min_fga = season_fga >= 50
                
                passes_filters = minutes_stable and min_volume and min_fga
                
                if passes_filters:
                    filtered_record = base_record.copy()
                    filtered_record['filter_status'] = 'PASSED'
                    results_filtered.append(filtered_record)
    
    # Convert to DataFrames
    df_base = pd.DataFrame(results_base)
    df_filtered = pd.DataFrame(results_filtered)
    
    # Print comparison
    print(f"📈 RESULTS COMPARISON")
    print(f"{'='*70}\n")
    
    if len(df_base) > 0:
        print(f"🔹 BASELINE (No Filters):")
        print(f"   Total signals: {len(df_base)}")
        print(f"   BUY_LOW: {len(df_base[df_base['signal'] == 'BUY_LOW'])}")
        print(f"   SELL_HIGH: {len(df_base[df_base['signal'] == 'SELL_HIGH'])}")
        print(f"   Overall hit rate: {df_base['regression_occurred'].mean():.1%}")
        print(f"   BUY_LOW hit rate: {df_base[df_base['signal'] == 'BUY_LOW']['regression_occurred'].mean():.1%}")
        print(f"   SELL_HIGH hit rate: {df_base[df_base['signal'] == 'SELL_HIGH']['regression_occurred'].mean():.1%}")
    
    print(f"\n🔹 FILTERED (Minutes Stable + 15+ MPG + 50+ FGA):")
    if len(df_filtered) > 0:
        print(f"   Total signals: {len(df_filtered)}")
        print(f"   BUY_LOW: {len(df_filtered[df_filtered['signal'] == 'BUY_LOW'])}")
        print(f"   SELL_HIGH: {len(df_filtered[df_filtered['signal'] == 'SELL_HIGH'])}")
        print(f"   Overall hit rate: {df_filtered['regression_occurred'].mean():.1%}")
        print(f"   BUY_LOW hit rate: {df_filtered[df_filtered['signal'] == 'BUY_LOW']['regression_occurred'].mean():.1%}")
        print(f"   SELL_HIGH hit rate: {df_filtered[df_filtered['signal'] == 'SELL_HIGH']['regression_occurred'].mean():.1%}")
        
        # Calculate improvement
        base_rate = df_base['regression_occurred'].mean()
        filtered_rate = df_filtered['regression_occurred'].mean()
        improvement = (filtered_rate - base_rate) * 100
        
        print(f"\n   📊 Improvement: {improvement:+.1f} percentage points")
        print(f"   📊 Signals removed: {len(df_base) - len(df_filtered)} ({(1 - len(df_filtered)/len(df_base))*100:.1f}%)")
    else:
        print(f"   ⚠️  No signals passed filters")
    
    # Show filtered-out cases
    print(f"\n{'='*70}")
    print(f"🚫 FILTERED OUT CASES (Why they were removed)")
    print(f"{'='*70}\n")
    
    filtered_out = [r for r in results_base if r not in results_filtered]
    if filtered_out:
        df_filtered_out = pd.DataFrame(filtered_out)
        
        # Analyze why they were filtered
        for _, row in df_filtered_out.head(10).iterrows():
            reasons = []
            if row['season_min'] < 15:
                reasons.append(f"Low MPG ({row['season_min']:.1f})")
            if abs(row['l5_min'] - row['season_min']) / row['season_min'] > 0.20:
                reasons.append(f"Minutes unstable (L5={row['l5_min']:.1f} vs Season={row['season_min']:.1f})")
            
            print(f"  {row['player']:25s} {row['game_date']:12s} {row['signal']:10s} - {', '.join(reasons)}")
    
    # Save results
    df_base.to_csv('regression_backtest_baseline.csv', index=False)
    df_filtered.to_csv('regression_backtest_filtered.csv', index=False)
    
    print(f"\n💾 Results saved:")
    print(f"   - regression_backtest_baseline.csv (all signals)")
    print(f"   - regression_backtest_filtered.csv (filtered signals)")
    print(f"\n{'='*70}\n")
    
    return df_base, df_filtered


if __name__ == "__main__":
    df_base, df_filtered = backtest_with_filters(lookback_days=60)
