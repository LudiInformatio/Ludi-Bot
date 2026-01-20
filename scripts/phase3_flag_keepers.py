"""
Flag questionable keepers from keepers.csv and write flagged_keepers.csv
"""
import csv

def run():
    infile='keepers.csv'
    outfile='flagged_keepers.csv'
    flags=[]
    with open(infile,newline='',encoding='utf-8') as f:
        r=csv.DictReader(f)
        rows=list(r)
    for row in rows:
        reasons=[]
        name=row['player_name']
        keeper=row['keeper_id']
        ids=row['ids'].split(';') if row['ids'] else []
        try:
            best=int(row.get('best_score') or 0)
        except:
            best=0
        if keeper in ('UNKNOWN','GHOST',''):
            reasons.append('keeper_placeholder')
        if best<=2:
            reasons.append('low_completeness')
        if (not keeper.isdigit()) and any(i.isdigit() for i in ids):
            reasons.append('keeper_non_numeric_but_numeric_ids_exist')
        if reasons:
            flags.append({'player_name':name,'keeper_id':keeper,'ids':';'.join(ids),'best_score':best,'reasons':';'.join(reasons)})
    with open(outfile,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['player_name','keeper_id','ids','best_score','reasons'])
        w.writeheader()
        for r in flags:
            w.writerow(r)
    print('flagged count:', len(flags))
    for i,r in enumerate(flags[:20],1):
        print(i, r['player_name'], r['keeper_id'], 'best_score=', r['best_score'], 'reasons=', r['reasons'])

if __name__=='__main__':
    run()
