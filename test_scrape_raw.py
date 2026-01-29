import pandas as pd
from io import StringIO
from playwright.sync_api import sync_playwright
from utils.mappings import resolve_team_abbr

def test_scrape():
    url = "https://official.nba.com/referee-assignments/"
    print(f"Scraping {url}...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # Try networkidle for a more complete load
            page.goto(url, wait_until="networkidle", timeout=90000)
            
            print("Clicking GO button...")
            page.wait_for_selector('input#date-filter', timeout=20000)
            page.click('input#date-filter')
            
            print("Waiting for table...")
            page.wait_for_selector(".nba-refs-content table tbody tr", timeout=30000)
            
            content = page.content()
            dfs = pd.read_html(StringIO(content))
            
            if not dfs:
                print("No tables found.")
                return

            df = dfs[0]
            df.columns = [c.upper() for c in df.columns]
            print("\nTable Columns:", df.columns.tolist())
            
            print("\nRaw Data Snippet:")
            print(df[['GAME', 'CHIEF' if 'CHIEF' in df.columns else df.columns[1]]].head())
            
            for _, row in df.iterrows():
                game_str = str(row.get('GAME', ''))
                if '@' in game_str:
                    parts = game_str.split('@')
                    raw_home = parts[1].strip()
                    if '(' in raw_home:
                        raw_home = raw_home.split('(')[0].strip()
                    
                    abbr = resolve_team_abbr(raw_home)
                    print(f"Game: {game_str} | Raw Home: '{raw_home}' | Resolved: '{abbr}'")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    test_scrape()
