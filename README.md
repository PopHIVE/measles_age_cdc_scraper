# CDC Measles Case Data Scraper

Automated pipeline for collecting and structuring weekly CDC measles surveillance data. The scraper captures data from the [CDC Measles Cases and Outbreaks](https://www.cdc.gov/measles/data-research/index.html) page — both the live site and historical snapshots via the Wayback Machine — and parses it into a structured CSV.

## Output

**`measles_structured.csv`** — one row per CDC update week with the following columns:

| Column | Description |
|---|---|
| `snapshot_date` | Date the page was captured (YYYY-MM-DD) |
| `update_date` | CDC's stated data update date |
| `total_cases` | Total confirmed measles cases |
| `age_under5_n`, `age_under5_pct` | Cases among children under 5 (count and %) |
| `age_5_19_n`, `age_5_19_pct` | Cases among ages 5–19 |
| `age_20plus_n`, `age_20plus_pct` | Cases among adults 20+ |
| `age_unknown_n`, `age_unknown_pct` | Cases with unknown age |
| `vax_unvax_or_unknown_pct` | % unvaccinated or unknown vaccination status |
| `vax_one_mmr_pct` | % with one MMR dose |
| `vax_two_mmr_pct` | % with two MMR doses |
| `hosp_total_n`, `hosp_total_pct` | Total hospitalizations (count and %) |
| `hosp_under5_n`, `hosp_under5_pct` | Hospitalizations among under 5 |
| `hosp_5_19_n`, `hosp_5_19_pct` | Hospitalizations among 5–19 |
| `hosp_20plus_n`, `hosp_20plus_pct` | Hospitalizations among 20+ |
| `hosp_unknown_n`, `hosp_unknown_pct` | Hospitalizations with unknown age |

Missing values are coded as `NA`.

## How it works

1. **`measles_cdc_scraper.py`** uses [Playwright](https://playwright.dev/python/) to render the CDC page in a headless Chromium browser and extract the visible text. This is necessary because the page uses JavaScript to render its data tables.

2. Each scraped page is cached as a plain text file in **`raw/`** (named by timestamp, e.g., `raw/20260304022912.txt`). Pages that are already cached are skipped on subsequent runs.

3. **`parse_raw_to_csv.py`** reads all files in `raw/` and extracts structured fields into `measles_structured.csv`.

4. The Wayback Machine CDX API is used to discover all historical snapshots, deduplicated to **one per CDC update week** (CDC updates on Tuesdays).

## Setup

```bash
pip install playwright
playwright install chromium
```

## Usage

```bash
# Scrape the live CDC page + backfill any missing Wayback Machine history
python measles_cdc_scraper.py

# Scrape the live CDC page only (used by the GitHub Action)
python measles_cdc_scraper.py --live

# Backfill Wayback Machine history only
python measles_cdc_scraper.py --history

# Re-parse all raw files into the structured CSV
python parse_raw_to_csv.py
```

## Automated weekly updates

A GitHub Action (`.github/workflows/weekly-scrape.yml`) runs every **Wednesday at 10:00 UTC** — the day after the CDC's Tuesday data update. It:

1. Scrapes the live CDC page
2. Parses all raw files into `measles_structured.csv`
3. Commits and pushes any new data

The workflow can also be triggered manually from the Actions tab.

## Repository structure

```
measles_age_cdc_scraper/
  measles_cdc_scraper.py      # Main scraper (Playwright + Wayback Machine)
  parse_raw_to_csv.py         # Parser: raw text -> structured CSV
  measles_structured.csv      # Output: structured weekly data
  measles_cases_parser.html   # Browser-based parser tool (standalone)
  cdc_measles_urls.txt        # Tracked Wayback Machine snapshot URLs
  raw/                        # Cached scraped text (one .txt per snapshot)
  requirements.txt            # Python dependencies
  .github/workflows/          # GitHub Actions for weekly automation
```

## Data source

All data originates from the CDC's [Measles Cases and Outbreaks](https://www.cdc.gov/measles/data-research/index.html) page. Historical data is retrieved via the [Wayback Machine](https://web.archive.org/).
