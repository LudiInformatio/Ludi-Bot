import sqlite3
import pandas as pd
import numpy as np

DB_PATH = "ludi.db"

def analyze_effectiveness():
    print("==================================================")
    print("LUDI INFORMATIO: WEEK 3 VALIDATION ANALYSIS")
    print("==================================================")
    
    conn = sqlite3.connect(DB_PATH)
    
    # Load settled bets
    query = '''
        SELECT *
        FROM bet_recommendations
        WHERE outcome IN ('WIN', 'LOSS', 'PUSH')
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("❌ No settled bets found for analysis.")
        return

    print(f"📊 Analyzing {len(df)} settled bets from {df['game_date'].min()} to {df['game_date'].max()}\n")
    
    # --- 1. OVERALL METRICS ---
    total_bets = len(df)
    wins = len(df[df['outcome'] == 'WIN'])
    losses = len(df[df['outcome'] == 'LOSS'])
    pushes = len(df[df['outcome'] == 'PUSH'])
    hit_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    pnl = df['profit_loss'].sum()
    roi = (pnl / df['units'].sum()) * 100 if df['units'].sum() > 0 else 0
    
    # Calculate RMSE
    # RMSE = sqrt(mean((actual - proj)^2))
    df['error_sq'] = (df['actual_result'] - df['projection']) ** 2
    mse = df['error_sq'].mean()
    rmse = np.sqrt(mse)
    
    print("--- 🌍 GLOBAL PERFORMANCE ---")
    print(f"  Bets:      {total_bets}")
    print(f"  Record:    {wins}-{losses}-{pushes}")
    print(f"  Hit Rate:  {hit_rate:.1f}%")
    print(f"  Units:     {pnl:+.2f}u")
    print(f"  ROI:       {roi:+.1f}%")
    print(f"  RMSE:      {rmse:.2f}")

    # --- 2. BY ARCHETYPE ---
    print("\n--- ⛹️ BY ARCHETYPE ---")
    if 'archetype' in df.columns:
        arch_stats = df.groupby('archetype').apply(
            lambda x: pd.Series({
                'bets': len(x),
                'hit_rate': (len(x[x['outcome']=='WIN']) / len(x[x['outcome']!='PUSH'])) * 100 if len(x[x['outcome']!='PUSH']) > 0 else 0,
                'pnl': x['profit_loss'].sum(),
                'avg_error': (x['actual_result'] - x['projection']).abs().mean()
            })
        ).sort_values('bets', ascending=False)
        print(arch_stats)
    else:
        print("Wait - archetype column missing from dataframe?")

    # --- 3. BY STAT CATEGORY ---
    print("\n--- 📈 BY STAT ---")
    stat_stats = df.groupby('stat_category').apply(
        lambda x: pd.Series({
            'bets': len(x),
            'hit_rate': (len(x[x['outcome']=='WIN']) / len(x[x['outcome']!='PUSH'])) * 100 if len(x[x['outcome']!='PUSH']) > 0 else 0,
            'rmse': np.sqrt(((x['actual_result'] - x['projection']) ** 2).mean())
        })
    ).sort_values('bets', ascending=False)
    print(stat_stats)

    # --- 4. BY EDGE BUCKET ---
    print("\n--- 🔪 BY EDGE (EV) ---")
    # bucket ev: 0-5%, 5-10%, 10-20%, 20%+
    bins = [0, 5, 10, 20, 100]
    labels = ['Low (0-5%)', 'Med (5-10%)', 'High (10-20%)', 'Smash (20%+)']
    df['edge_bucket'] = pd.cut(df['ev'], bins=bins, labels=labels)
    
    edge_stats = df.groupby('edge_bucket', observed=False).apply(
        lambda x: pd.Series({
            'bets': len(x),
            'hit_rate': (len(x[x['outcome']=='WIN']) / len(x[x['outcome']!='PUSH'])) * 100 if len(x[x['outcome']!='PUSH']) > 0 else 0,
            'pnl': x['profit_loss'].sum()
        })
    )
    print(edge_stats)
    
    # --- 5. REF IMPACT ---
    print("\n--- 🦓 REF IMPACT ---")
    # bucket ref impact
    df['ref_bucket'] = pd.cut(df['referee_impact'], bins=[0, 0.95, 1.05, 2.0], labels=['Slow (<0.95)', 'Neutral', 'Fast (>1.05)'])
    ref_stats = df.groupby('ref_bucket', observed=False).apply(
        lambda x: pd.Series({
            'bets': len(x),
            'hit_rate': (len(x[x['outcome']=='WIN']) / len(x[x['outcome']!='PUSH'])) * 100 if len(x[x['outcome']!='PUSH']) > 0 else 0,
            'avg_pts_diff': (x['actual_result'] - x['projection']).mean()
        })
    )
    print(ref_stats)

    print("\n==================================================")
    print("✅ ANALYSIS COMPLETE")

if __name__ == "__main__":
    analyze_effectiveness()
