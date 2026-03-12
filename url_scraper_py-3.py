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

URLS = [
    "https://web.archive.org/web/20260304022912/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20260226022109/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20260219082434/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20260212041107/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20260205125741/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20260129055811/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20260122043835/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20260108073126/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20260107085029/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20251230211653/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20251222182118/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20251216192914/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20251209174524/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20251201135237/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20251125123810/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20251118121655/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20251112194142/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20251109185844/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20251104095354/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20251029131356/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20251021132050/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20251015072202/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20251007190147/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250930192816/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250923192759/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250916172209/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250909211703/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250902141655/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250826192651/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250819212746/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250805192903/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250729130523/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250722163010/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250715201043/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250708192645/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250701192738/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250624192701/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250617192823/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250612210526/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250605071309/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250529220521/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250522104501/https://www.cdc.gov/measles/data-research/index.html", 
    "https://web.archive.org/web/20250515230033/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250507184209/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250501130832/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250424192417/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250417234734/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250410194606/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250403193119/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250327223649/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250320235609/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250312223228/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250306170908/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250227021517/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250220144344/https://www.cdc.gov/measles/data-research/index.html",
    "https://web.archive.org/web/20250203191249/https://www.cdc.gov/measles/data-research/index.html"
    # Add more URLs here, one per line:
        # "https://web.archive.org/web/20250901000000/https://www.cdc.gov/measles/data-research/index.html",
]

OUTPUT_FILE = os.path.expanduser("~/Desktop/output.txt")
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
