"""
CDC URL Text Scraper — Playwright version
------------------------------------------
Uses a real browser (Chromium) to fetch fully JavaScript-rendered page text,
equivalent to doing Ctrl+A, Ctrl+C in your browser.

Features:
    - Scrapes live CDC page (--live) or historical Wayback Machine snapshots
    - Auto-discovers new Wayback Machine snapshots via CDX API
    - Caches scraped pages in raw/ folder to avoid re-scraping
    - Weekly deduplication: only 1 snapshot per CDC update week

Requirements:
    pip install playwright
    playwright install chromium

Usage:
    python measles_cdc_scraper.py          # scrape live CDC page + backfill history
    python measles_cdc_scraper.py --live   # scrape live CDC page only
    python measles_cdc_scraper.py --history  # backfill Wayback Machine history only
"""

from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import argparse
import json
import time
import os
import re
import urllib.request

# ── Configuration ─────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
URL_FILE = os.path.join(SCRIPT_DIR, "cdc_measles_urls.txt")
RAW_DIR = os.path.join(SCRIPT_DIR, "raw")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "output.txt")
WAIT_SECONDS = 4      # Seconds to wait after page load for JS to finish rendering
TIMEOUT_MS   = 30000  # Page load timeout in milliseconds

CDC_URL = "https://www.cdc.gov/measles/data-research/index.html"
CDX_API = (
    "https://web.archive.org/cdx/search/cdx"
    f"?url={CDC_URL}"
    "&output=json&fl=timestamp,statuscode"
    "&filter=statuscode:200&from=20250101"
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def cdc_week_key(ts):
    """Return the Tuesday that starts the CDC update week for a given timestamp."""
    dt = datetime.strptime(ts[:8], "%Y%m%d")
    days_since_tuesday = (dt.weekday() - 1) % 7
    tuesday = dt - timedelta(days=days_since_tuesday)
    return tuesday.strftime("%Y%m%d")


def load_url_file(path):
    """Read URLs from file, stripping quotes and whitespace."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig") as f:
        urls = []
        for line in f:
            cleaned = line.strip().strip('"\u201c\u201d')
            if cleaned and cleaned.startswith("http"):
                urls.append(cleaned)
        return urls


def extract_timestamp(url):
    """Extract the 14-digit Wayback timestamp from an archive URL."""
    m = re.search(r"/web/(\d{14})/", url)
    return m.group(1) if m else None

# ── Caching ───────────────────────────────────────────────────────────────────

def cache_path_for_ts(ts):
    """Return the cache file path for a given timestamp."""
    return os.path.join(RAW_DIR, f"{ts}.txt")


def cache_path(url):
    """Return the cache file path for a given archive URL."""
    ts = extract_timestamp(url)
    if ts:
        return cache_path_for_ts(ts)
    return None


def read_cache(url):
    """Read cached text for a URL, or return None if not cached."""
    path = cache_path(url)
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def write_cache_file(ts, text):
    """Write scraped text to the cache as a plain text file."""
    os.makedirs(RAW_DIR, exist_ok=True)
    path = cache_path_for_ts(ts)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_cache(url, text):
    """Write scraped text to the cache, keyed by Wayback timestamp."""
    ts = extract_timestamp(url)
    if ts:
        write_cache_file(ts, text)

# ── URL discovery ─────────────────────────────────────────────────────────────

def discover_new_urls():
    """Query the Wayback Machine CDX API for new snapshots and update the URL file."""
    print("Checking Wayback Machine for new snapshots...")
    existing_urls = load_url_file(URL_FILE)
    existing_timestamps = {extract_timestamp(u) for u in existing_urls}

    try:
        req = urllib.request.Request(CDX_API, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  Could not reach CDX API: {e}")
        print("  Continuing with existing URL list.")
        return existing_urls

    # data[0] is the header row ["timestamp", "statuscode"], rest are data rows
    if len(data) <= 1:
        print("  No snapshots found.")
        return existing_urls

    # CDC updates on Tuesdays. We only need one snapshot per update week.
    by_week = {}
    for row in data[1:]:
        ts = row[0]
        week = cdc_week_key(ts)
        if week not in by_week or ts < by_week[week]:
            by_week[week] = ts

    all_timestamps = sorted(by_week.values(), reverse=True)
    print(f"  CDX returned {len(data)-1} snapshots, reduced to {len(all_timestamps)} (1 per CDC week)")

    # Reduce existing URLs to 1-per-week, preferring URLs that are already cached
    existing_by_week = {}
    for url in existing_urls:
        ts = extract_timestamp(url)
        if ts:
            week = cdc_week_key(ts)
            prev = existing_by_week.get(week)
            if prev is None:
                existing_by_week[week] = url
            else:
                prev_cached = read_cache(prev) is not None
                this_cached = read_cache(url) is not None
                if this_cached and not prev_cached:
                    existing_by_week[week] = url
                elif not this_cached and not prev_cached and ts < extract_timestamp(prev):
                    existing_by_week[week] = url

    # Merge: for each week, prefer the existing URL if we already have one
    final_urls = []
    covered_weeks = set(existing_by_week.keys())
    for url in existing_by_week.values():
        final_urls.append(url)

    new_urls = []
    for ts in all_timestamps:
        week = cdc_week_key(ts)
        if week not in covered_weeks:
            url = f"https://web.archive.org/web/{ts}/{CDC_URL}"
            new_urls.append(url)
            final_urls.append(url)
            covered_weeks.add(week)

    if new_urls:
        print(f"  Found {len(new_urls)} new week(s) to scrape. Appending to {URL_FILE}")
        with open(URL_FILE, "a", encoding="utf-8") as f:
            for url in new_urls:
                f.write(f'"{url}"\n')
    else:
        print("  No new weeks found.")

    final_urls.sort(key=lambda u: extract_timestamp(u) or "", reverse=True)
    print(f"  Total URLs to process: {len(final_urls)} (1 per CDC update week)")
    return final_urls

# ── Core scraping ─────────────────────────────────────────────────────────────

def fetch_rendered_text(page, url):
    """Load a URL in a real browser and return its fully rendered plain text."""
    print(f"  Loading: {url}")
    page.goto(url, timeout=TIMEOUT_MS, wait_until="load")

    # Extra wait for any deferred JS rendering
    time.sleep(WAIT_SECONDS)

    # Extract innerText from body — equivalent to Ctrl+A, Ctrl+C visible text
    text = page.evaluate("() => document.body.innerText")

    # ── Trim to relevant section ───────────────────────────────────────────
    date_pattern = re.compile(
        r"(Jan(?:uary)?\.?|Feb(?:ruary)?\.?|Mar(?:ch)?\.?|Apr(?:il)?\.?|May\.?|"
        r"Jun(?:e)?\.?|Jul(?:y)?\.?|Aug(?:ust)?\.?|Sep(?:tember)?\.?|"
        r"Oct(?:ober)?\.?|Nov(?:ember)?\.?|Dec(?:ember)?\.?)"
        r"\s+\d{1,2},?\s+\d{4}",
        re.IGNORECASE
    )
    deaths_pattern = re.compile(r"U\.S\.?\s+Deaths", re.IGNORECASE)

    lines_raw = text.splitlines()
    start_idx = None
    end_idx   = None

    for i, line in enumerate(lines_raw):
        if start_idx is None and date_pattern.search(line.strip()):
            start_idx = i
        if deaths_pattern.search(line.strip()):
            end_idx = i
            break

    if start_idx is not None and end_idx is not None and end_idx > start_idx:
        lines_raw = lines_raw[start_idx:end_idx]
    elif start_idx is not None and end_idx is None:
        lines_raw = lines_raw[start_idx:]

    # Clean up excessive blank lines
    cleaned = []
    blank_count = 0
    for line in lines_raw:
        stripped = line.strip()
        if stripped == "":
            blank_count += 1
            if blank_count <= 2:
                cleaned.append("")
        else:
            blank_count = 0
            cleaned.append(stripped)

    return "\n".join(cleaned).strip()

# ── Live CDC scrape ───────────────────────────────────────────────────────────

def scrape_live():
    """Scrape the live CDC page and cache it with today's timestamp."""
    today = datetime.now().strftime("%Y%m%d%H%M%S")
    today_date = datetime.now().strftime("%Y%m%d")

    # Check if we already have a scrape for today
    existing = [f for f in os.listdir(RAW_DIR) if f.startswith(today_date)] if os.path.exists(RAW_DIR) else []
    if existing:
        print(f"Already have a scrape for today ({existing[0]}), skipping live scrape.")
        return

    print(f"Scraping live CDC page: {CDC_URL}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })

        try:
            text = fetch_rendered_text(page, CDC_URL)
            write_cache_file(today, text)
            print(f"  OK — {len(text):,} characters saved to raw/{today}.txt")
        except Exception as e:
            print(f"  ERROR scraping live page: {e}")

        browser.close()

# ── History scrape ────────────────────────────────────────────────────────────

def scrape_history():
    """Scrape Wayback Machine history URLs."""
    urls = discover_new_urls()
    if not urls:
        print("No URLs found.")
        return

    results = []
    errors  = []
    urls_to_scrape = []

    for url in urls:
        cached = read_cache(url)
        if cached is not None:
            results.append((url, cached))
        else:
            urls_to_scrape.append(url)

    print(f"\n{len(results)} cached, {len(urls_to_scrape)} to scrape.")

    if urls_to_scrape:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            })

            for i, url in enumerate(urls_to_scrape, 1):
                print(f"\n[{i}/{len(urls_to_scrape)}] Processing...")
                try:
                    text = fetch_rendered_text(page, url)
                    write_cache(url, text)
                    results.append((url, text))
                    print(f"  OK — {len(text):,} characters extracted.")
                except Exception as e:
                    print(f"  ERROR — {e}")
                    errors.append((url, str(e)))

            browser.close()

    # Sort results by timestamp (newest first)
    results.sort(key=lambda r: extract_timestamp(r[0]) or "", reverse=True)

    # Write output file
    divider = "\n" + ("=" * 80) + "\n"
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("CDC Measles Data — Scraped Text\n")
        f.write(f"URLs processed: {len(results)} succeeded, {len(errors)} failed\n")
        f.write(divider)

        for url, text in results:
            f.write(f"SOURCE: {url}\n")
            f.write(divider)
            f.write(text)
            f.write(divider)

        if errors:
            f.write("\nFAILED URLS:\n")
            for url, err in errors:
                f.write(f"  {url}\n    Error: {err}\n")

    print(f"\nDone! Output saved to: {os.path.abspath(OUTPUT_FILE)}")
    print(f"  {len(results)} page(s) saved, {len(errors)} failed.")


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CDC Measles Data Scraper")
    parser.add_argument("--live", action="store_true",
                        help="Scrape the live CDC page only")
    parser.add_argument("--history", action="store_true",
                        help="Backfill Wayback Machine history only")
    args = parser.parse_args()

    if args.live:
        scrape_live()
    elif args.history:
        scrape_history()
    else:
        # Default: scrape live + backfill history
        scrape_live()
        scrape_history()
