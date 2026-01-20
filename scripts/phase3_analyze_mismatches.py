#!/usr/bin/env python3
"""
Analyze `phase3_mismatches.csv` and summarize differing keys.
"""
import csv
import json
from collections import Counter
from pathlib import Path


def load_mismatches(path='phase3_mismatches.csv'):
    p = Path(path)
    if not p.exists():
        print('mismatches file not found:', path); return None
    rows = []
    with p.open('r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for rec in r:
            idv = rec['id']
            try:
                a = json.loads(rec['archived_json'])
            except Exception:
                a = rec['archived_json']
            try:
                l = json.loads(rec['log_json'])
            except Exception:
                l = rec['log_json']
            rows.append((idv, a, l))
    return rows


def diff_keys(a, b):
    if not isinstance(a, dict) or not isinstance(b, dict):
        return ['non-dict']
    keys = set(a.keys()) | set(b.keys())
    diffs = []
    for k in keys:
        if a.get(k) != b.get(k):
            diffs.append(k)
    return diffs


def main():
    rows = load_mismatches()
    if rows is None:
        return 2
    key_counter = Counter()
    sample = []
    for idv, a, l in rows:
        ks = diff_keys(a, l)
        for k in ks:
            key_counter[k] += 1
        if len(sample) < 10:
            sample.append((idv, ks))

    print('total mismatches:', len(rows))
    print('top differing keys:')
    for k, c in key_counter.most_common(20):
        print(f'- {k}: {c}')
    print('\nSample differences (up to 10):')
    for idv, ks in sample:
        print('-', idv, ks)


if __name__ == '__main__':
    main()
