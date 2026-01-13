#!/usr/bin/env python3
"""
LUDI INFORMATIO | DB QUERY UTILITY
====================================
A drop-in replacement for the 'sqlite3' CLI tool.
Allows running SQL queries from the command line using the Python environment.

Usage:
    ./query_db.py "SELECT * FROM player_game_tracking LIMIT 5"
    ./query_db.py "SELECT COUNT(*) FROM games" --table
"""

import sqlite3
import sys
import argparse
from tabulate import tabulate # We might not have this, so I'll stick to basic formatting first

def run_query(query, db_path='ludi.db', show_header=True):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(query)
        
        # Get headers
        if c.description:
            headers = [description[0] for description in c.description]
            rows = c.fetchall()
            
            if not rows:
                print("No results found.")
            else:
                # Basic column width formatting
                cols = len(headers)
                col_widths = [len(h) for h in headers]
                
                # Calculate max widths based on data (capped at 50 to avoid massive overflow)
                for row in rows:
                    for i, val in enumerate(row):
                        w = len(str(val))
                        if w > col_widths[i]:
                            col_widths[i] = min(w, 50) 
                            
                # Print Header
                if show_header:
                    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
                    print("-" * len(header_line))
                    print(header_line)
                    print("-" * len(header_line))
                
                # Print Rows
                for row in rows:
                    print(" | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)))
                    
                print("-" * len(header_line))
                print(f"({len(rows)} rows)")
        else:
            # For UPDATE/DELETE/INSERT
            conn.commit()
            print(f"Query executed successfully. Rows affected: {c.rowcount}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run SQL query on ludi.db')
    parser.add_argument('query', help='SQL query to execute')
    args = parser.parse_args()
    
    run_query(args.query)
