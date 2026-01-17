import sqlite3

DB_PATH = "ludi.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT game_id, date FROM games WHERE date = '2025-11-14' LIMIT 1")
row = c.fetchone()
print(f"Raw row: {row}")
print(f"Type of game_id: {type(row[0])}")
conn.close()
