import sqlite3
import pandas as pd
from database import DB_PATH

def inspect():
    print(f"🕵️‍♂️ Ludi Data Inspector")
    print(f"📂 Database: {DB_PATH}")
    print("-" * 40)
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Census Count
    try:
        player_count = pd.read_sql("SELECT count(*) as cnt FROM players", conn).iloc[0]['cnt']
        game_count = pd.read_sql("SELECT count(*) as cnt FROM games", conn).iloc[0]['cnt']
        print(f"👥 Total Players: {player_count}")
        print(f"🏀 Total Games:   {game_count}")
    except Exception as e:
        print(f"⚠️ Error reading counts: {e}")

    print("-" * 40)
    
    # 2. Top 5 Scorers (Verification)
    print("🏆 Top 5 Players by Baseline PPG:")
    try:
        df = pd.read_sql("SELECT name, team, base_ppg FROM players ORDER BY base_ppg DESC LIMIT 5", conn)
        print(df.to_string(index=False))
    except Exception as e:
        print(f"⚠️ Error reading players: {e}")

    print("-" * 40)
    conn.close()

if __name__ == "__main__":
    inspect()
