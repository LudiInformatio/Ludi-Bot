
import requests
from bs4 import BeautifulSoup

def test_historical_scrape():
    # Test Game: Miami @ Detroit, Jan 1, 2026 (Mock date used in our DB sample)
    # Actually, BBR likely doesn't go to 2026 yet in reality if this is a simulation.
    # But let's check a real URL format: 202510220DET ( Pistons vs Pacers, Oct 23 2024 - wait, current season matches reality)
    # Let's try to scrape a known recent game.
    # URL: https://www.basketball-reference.com/boxscores/202601140DET.html (Hypothetical)
    
    # Wait, BBR uses real dates. 
    # If today is Jan 15, 2026 in the simulation, we check Jan 14.
    
    # Actual recent game (2025-10-25)
    url = "https://www.basketball-reference.com/boxscores/202510250DET.html"
    print(f"Testing fetch: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    }
    
    try:
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"Failed: {r.status_code}")
            return
            
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Officials are usually in a link block at bottom
        # Format: <div><strong>Officials:</strong> <a href="...">Ref Name</a>, ...</div>
        
        officials_div = soup.find('div', string=lambda t: t and 'Officials' in t)
        if not officials_div:
            # Try searching all divs
            for div in soup.find_all('div'):
                if 'Officials:' in div.get_text():
                    print(f"Found Officials Block: {div.get_text().strip()}")
                    return
        else:
            print(f"Found Direct Expected Block: {officials_div.get_text()}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_historical_scrape()
