#!/usr/bin/env python3
"""
Check Company Resources — URL Reachability Validator
=====================================================
Parses employees/COMPANY_RESOURCES.md and validates that all external URLs
are reachable via HTTP HEAD requests. Intended for periodic health checks
(manual or GH Actions).

Usage:
    python scripts/check_company_resources.py             # check all URLs
    python scripts/check_company_resources.py --dry-run    # list URLs without checking
    python scripts/check_company_resources.py --verbose    # show response headers

Created: 2026-03-14 | Phase 8
"""

import argparse
import os
import re
import sys
import urllib.request
import urllib.error

# ─── Path Setup ───────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)

RESOURCES_PATH = os.path.join(_PROJECT_ROOT, 'employees', 'COMPANY_RESOURCES.md')

# Regex to extract HTTP/HTTPS URLs from markdown table cells
# Stops at whitespace, pipe character, or closing paren (common markdown delimiters)
URL_PATTERN = re.compile(r'https?://[^\s|)]+')

# Request timeout in seconds
REQUEST_TIMEOUT = 10


# ─── URL Extraction ──────────────────────────────────────────────────────────
def extract_urls(filepath: str) -> list[str]:
    """
    Read a markdown file and extract all HTTP/HTTPS URLs.
    Returns a deduplicated list preserving first-seen order.
    """
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        sys.exit(1)

    with open(filepath, 'r') as f:
        content = f.read()

    raw_urls = URL_PATTERN.findall(content)

    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for url in raw_urls:
        # Strip trailing punctuation that regex might capture (period, comma)
        url = url.rstrip('.,;:')
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    return unique_urls


# ─── URL Check ───────────────────────────────────────────────────────────────
def check_url(url: str, verbose: bool = False) -> dict:
    """
    Send an HTTP HEAD request to the URL.
    Returns a dict with 'url', 'status', 'result', and optionally 'headers'.
    """
    result = {'url': url, 'status': '---', 'result': 'UNKNOWN', 'headers': None}

    req = urllib.request.Request(url, method='HEAD')
    # Some servers block bare urllib; set a reasonable User-Agent
    req.add_header('User-Agent', 'Ludi-Bot/1.0 (health-check)')

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            result['status'] = str(resp.status)
            result['result'] = 'OK'
            if verbose:
                result['headers'] = dict(resp.headers)
    except urllib.error.HTTPError as e:
        # Server responded but with an error status (4xx, 5xx)
        result['status'] = str(e.code)
        result['result'] = 'HTTP_ERROR'
        print(f"[WARN] {url} returned HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        # DNS failure, connection refused, etc.
        result['result'] = 'URL_ERROR'
        print(f"[ERROR] {url} unreachable: {e.reason}")
    except TimeoutError:
        result['result'] = 'TIMEOUT'
        print(f"[ERROR] {url} timed out after {REQUEST_TIMEOUT}s")
    except Exception as e:
        result['result'] = 'ERROR'
        print(f"[ERROR] {url} unexpected error: {e}")

    return result


# ─── Results Table ───────────────────────────────────────────────────────────
def print_results_table(results: list[dict], verbose: bool = False) -> None:
    """Print a formatted markdown-style results table."""
    # Calculate column widths dynamically based on longest URL
    max_url_len = max(len(r['url']) for r in results) if results else 30
    url_width = max(max_url_len, 3)  # minimum 3 for header "URL"

    header = f"| {'#':>3} | {'URL':<{url_width}} | {'Status':<6} | {'Result':<10} |"
    sep = f"|{'─' * 5}|{'─' * (url_width + 2)}|{'─' * 8}|{'─' * 12}|"

    print(header)
    print(sep)

    for i, r in enumerate(results, 1):
        print(f"| {i:>3} | {r['url']:<{url_width}} | {r['status']:<6} | {r['result']:<10} |")
        if verbose and r.get('headers'):
            for key, val in r['headers'].items():
                print(f"|     |   {key}: {val}")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check Company Resources — validate external URL reachability"
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Extract and print URLs without making HTTP requests.')
    parser.add_argument('--verbose', action='store_true',
                        help='Print response headers for each URL.')
    args = parser.parse_args()

    print("=" * 60)
    print("CHECK COMPANY RESOURCES")
    print(f"Source: {RESOURCES_PATH}")
    print("=" * 60)

    # ── Extract URLs ───────────────────────────────────────────────────────
    urls = extract_urls(RESOURCES_PATH)

    if not urls:
        print("[WARN] No URLs found in COMPANY_RESOURCES.md")
        sys.exit(1)

    print(f"\nFound {len(urls)} unique URLs\n")

    # ── Dry run: just list URLs and exit ───────────────────────────────────
    if args.dry_run:
        print("DRY RUN — no HTTP requests will be made\n")
        for i, url in enumerate(urls, 1):
            print(f"  {i:>2}. {url}")
        print(f"\n{len(urls)} URLs extracted. Dry run complete.")
        sys.exit(0)

    # ── Check each URL ─────────────────────────────────────────────────────
    results = []
    for url in urls:
        result = check_url(url, verbose=args.verbose)
        results.append(result)

    # ── Print results table ────────────────────────────────────────────────
    print()
    print_results_table(results, verbose=args.verbose)

    # ── Summary ────────────────────────────────────────────────────────────
    ok_count = sum(1 for r in results if r['result'] == 'OK')
    fail_count = len(results) - ok_count
    print(f"\n{ok_count}/{len(results)} URLs reachable ({fail_count} failed)")

    if fail_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
