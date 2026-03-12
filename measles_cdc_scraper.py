"""
CDC URL Text Scraper — Playwright version
------------------------------------------
Uses a real browser (Chromium) to fetch fully JavaScript-rendered page text,
equivalent to doing Ctrl+A, Ctrl+C in your browser.

Requirements:
    pip install playwright
    playwright install chromium

Usage:
    1. Add your URLs to the URLS list below.
    2. Run:  python scraper.py
    3. Output is saved to:  output.txt  (in the same folder)
"""

from playwright.sync_api import sync_playwright
import time
import os
import re

# ── Configuration ─────────────────────────────────────────────────────────────
file_path = 'cdc_measles_urls.txt'

with open(file_path, 'r') as f:
    URL_list = [line.strip() for line in f]

URLS = URL_list

# CHANGE THIS 
OUTPUT_FILE = os.path.expanduser("~/output.txt")
WAIT_SECONDS = 4      # Seconds to wait after page load for JS to finish rendering
TIMEOUT_MS   = 30000  # Page load timeout in milliseconds

# ── Core function ─────────────────────────────────────────────────────────────

def fetch_rendered_text(page, url):
    """Load a URL in a real browser and return its fully rendered plain text."""
    print(f"  Loading: {url}")
    page.goto(url, timeout=TIMEOUT_MS, wait_until="load")

    # Extra wait for any deferred JS rendering
    time.sleep(WAIT_SECONDS)

    # Extract innerText from body — equivalent to Ctrl+A, Ctrl+C visible text
    text = page.evaluate("() => document.body.innerText")

    # ── Trim to relevant section ───────────────────────────────────────────
    # Start: first date-like line on the page (e.g. "Oct. 8, 2025" or "June 13, 2025")
    # End:   the "U.S. Deaths" heading (exclusive)
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


def scrape_urls(urls, output_file):
    """Scrape all URLs using a headless browser and write to output_file."""
    results = []
    errors  = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Set a realistic user agent
        page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing...")
            try:
                text = fetch_rendered_text(page, url)
                results.append((url, text))
                print(f"  OK — {len(text):,} characters extracted.")
            except Exception as e:
                print(f"  ERROR — {e}")
                errors.append((url, str(e)))

        browser.close()

    # Write output file
    divider = "\n" + ("=" * 80) + "\n"
    with open(output_file, "w", encoding="utf-8") as f:
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

    print(f"\nDone! Output saved to: {os.path.abspath(output_file)}")
    print(f"  {len(results)} page(s) saved, {len(errors)} failed.")


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not URLS:
        print("No URLs provided. Add URLs to the URLS list and run again.")
    else:
        scrape_urls(URLS, OUTPUT_FILE)
