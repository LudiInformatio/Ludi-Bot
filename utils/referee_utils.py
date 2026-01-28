import time
import requests
import logging
import unicodedata
from typing import Optional
from bs4 import BeautifulSoup
import pandas as pd


def http_get_with_retries(url: str, headers: dict = None, max_attempts: int = 3, backoff: float = 2.0, timeout: int = 20) -> Optional[str]:
    """Perform HTTP GET with simple exponential backoff retries. Returns response.text or raises.
    """
    headers = headers or {}
    attempt = 0
    while attempt < max_attempts:
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.text
        except Exception as e:
            attempt += 1
            wait = backoff * (2 ** (attempt - 1))
            logging.warning(f"HTTP GET attempt {attempt}/{max_attempts} failed for {url}: {e}; retrying in {wait}s")
            time.sleep(wait)
    logging.error(f"HTTP GET failed after {max_attempts} attempts: {url}")
    return None


def parse_assignments_with_bs4(html: str) -> Optional[pd.DataFrame]:
    """Fallback parser: find first table-like structure and convert to DataFrame.
    Returns DataFrame or None.
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Try to find any table
    table = soup.find('table')
    if not table:
        # Try to find generic assignment cards (divs) and build a table-like structure
        cards = soup.find_all(class_=lambda x: x and 'assignment' in x.lower())
        if not cards:
            return None
        rows = []
        for card in cards:
            text = ' | '.join(t.get_text(strip=True) for t in card.find_all(['p', 'div', 'span']))
            rows.append([text])
        return pd.DataFrame(rows)

    # Extract headers
    headers = []
    head = table.find('thead')
    if head:
        headers = [th.get_text(strip=True) for th in head.find_all('th')]
    else:
        # fallback: use first row as header if it has th/strong
        first_row = table.find('tr')
        if first_row:
            headers = [cell.get_text(strip=True) for cell in first_row.find_all(['th', 'td'])]

    # Extract rows
    data = []
    for tr in table.find_all('tr'):
        cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
        if cells:
            data.append(cells)

    if not data:
        return None

    # If headers look like the first row, remove it from data
    if headers and data and data[0] == headers:
        data = data[1:]

    try:
        df = pd.DataFrame(data)
        if headers and len(headers) == df.shape[1]:
            df.columns = headers
        return df
    except Exception:
        return None


def normalize_team_key(raw: str, team_map: dict) -> Optional[str]:
    """Normalize a raw team string into a 3-letter team abbr using provided team_map."""
    if not raw:
        return None

    # Normalize unicode and remove periods
    s = unicodedata.normalize('NFKD', raw)
    s = s.replace('.', '').strip()

    # Direct map
    if s in team_map:
        return team_map[s]

    # Case-insensitive contains match
    for key, abbr in team_map.items():
        if key.lower() in s.lower():
            return abbr

    # If looks like a 3-letter code
    if len(s) == 3 and s.isalpha():
        return s.upper()

    return None
