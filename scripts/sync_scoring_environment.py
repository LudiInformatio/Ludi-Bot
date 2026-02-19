import sqlite3, json, os, datetime

DB_PATH = 'ludi.db'
OUT_PATH = 'cache/scoring_environment.json'

conn = sqlite3.connect(DB_PATH)

conn.execute("""
    UPDATE bet_recommendations
    SET opponent = CASE
        WHEN team = home_team THEN away_team
        WHEN team = away_team THEN home_team
        ELSE NULL
    END
    WHERE (opponent IS NULL OR opponent = '')
      AND home_team IS NOT NULL AND away_team IS NOT NULL AND team IS NOT NULL
""")
conn.commit()

cutoff = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
rows = conn.execute("""
    SELECT stat_category, bet_side,
           COUNT(*) as bets,
           AVG(CASE WHEN outcome='WIN' THEN 1.0 ELSE 0 END) as hit_rate
    FROM bet_recommendations
    WHERE outcome IN ('WIN','LOSS') AND game_date >= ?
    GROUP BY stat_category, bet_side HAVING bets >= 20
""", (cutoff,)).fetchall()

over_row = conn.execute("""
    SELECT COUNT(*) as bets,
           AVG(CASE WHEN outcome='WIN' THEN 1.0 ELSE 0 END) as over_rate
    FROM bet_recommendations
    WHERE outcome IN ('WIN','LOSS') AND bet_side='OVER' AND game_date >= ?
""", (cutoff,)).fetchone()

conn.close()

if not over_row or over_row[0] < 100:
    print("Insufficient data — skipping write")
    exit(0)

by_stat = {}
for stat, side, bets, rate in rows:
    by_stat.setdefault(stat.lower(), {})[side.lower()] = round(rate, 3)

over_rate = round(over_row[1], 3)
if over_rate < 0.48:
    env = "UNDER_FAVORED"
elif over_rate > 0.54:
    env = "OVER_FAVORED"
else:
    env = "NEUTRAL"

output = {
    "over_hit_rate_14d": over_rate,
    "by_stat": by_stat,
    "sample_size": over_row[0],
    "environment": env,
    "computed_at": datetime.datetime.now().isoformat()
}

os.makedirs('cache', exist_ok=True)
with open(OUT_PATH, 'w') as f:
    json.dump(output, f, indent=2)

print(f"Scoring env: {env} ({over_rate:.1%} OVER rate, n={over_row[0]})")
