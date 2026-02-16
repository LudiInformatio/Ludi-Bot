import sqlite3, csv, sys

def main(db='ludi.db.test'):
    conn=sqlite3.connect(db)
    cur=conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables=[r[0] for r in cur.fetchall()]
    cols_map={}
    for t in tables:
        cur.execute(f"PRAGMA table_info({t})")
        cols=[r[1] for r in cur.fetchall()]
        cols_map[t]=cols

    not_found=[]
    found=0
    total=0
    with open('keepers.csv', newline='', encoding='utf-8') as f:
        reader=csv.DictReader(f)
        for r in reader:
            total+=1
            keeper=r['keeper_id']
            if keeper=='' or keeper is None:
                not_found.append((r['player_name'],keeper))
                continue
            found_any=False
            for t,cols in cols_map.items():
                for c in cols:
                    try:
                        q=f"SELECT 1 FROM {t} WHERE CAST({c} AS TEXT)=? LIMIT 1"
                        cur.execute(q,(keeper,))
                        if cur.fetchone():
                            found_any=True
                            break
                    except Exception:
                        continue
                if found_any:
                    break
            if found_any:
                found+=1
            else:
                not_found.append((r['player_name'],keeper))

    print('keepers total:', total)
    print('keepers found in DB:', found)
    print('keepers missing:', len(not_found))
    if not_found:
        print('\nSample missing (up to 20):')
        for i,(name,k) in enumerate(not_found[:20],1):
            print(i, name, k)

if __name__=='__main__':
    db = sys.argv[1] if len(sys.argv)>1 else 'ludi.db.test'
    main(db)
