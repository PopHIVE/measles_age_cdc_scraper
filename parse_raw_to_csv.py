"""
Parse raw scraped CDC measles text files into a structured CSV.

Reads all .txt files from raw/ and extracts:
  - Total cases, cases by age group, vaccination status
  - Hospitalizations overall and by age group
  - Both counts and percentages where available

Output: measles_structured.csv
"""

import csv
import os
import re
import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "raw")
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "measles_structured.csv")


def parse_update_date(text):
    """Extract the 'Updated on ...' date from the text."""
    m = re.search(
        r"Updated on (\w+ \d{1,2},? \d{4})", text, re.IGNORECASE
    )
    return m.group(1) if m else None


def parse_total_cases(text):
    """Extract total confirmed cases from the prose paragraph."""
    # Match patterns like "a total of 1,648 confirmed*" or "1,136 confirmed*"
    m = re.search(
        r"(?:a total of\s+)?([\d,]+)\s+confirmed\*?\s+measles cases were reported",
        text, re.IGNORECASE
    )
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def parse_single_year(text):
    """Parse the compact 2025-only format (single column)."""
    data = {}

    # Age groups — compact format: "Under 5 years: 500 (26%)"
    for label, key in [
        (r"Under 5 years", "age_under5"),
        (r"5-19 years", "age_5_19"),
        (r"20\+ years", "age_20plus"),
        (r"Age unknown", "age_unknown"),
    ]:
        m = re.search(
            rf"{label}:\s*([\d,]+)\s*\((\d+)%\)", text
        )
        if m:
            data[f"{key}_n"] = int(m.group(1).replace(",", ""))
            data[f"{key}_pct"] = int(m.group(2))

    # Vaccination status — "Unvaccinated or Unknown: 92%"
    for label, key in [
        (r"Unvaccinated or Unknown", "vax_unvax_or_unknown"),
        (r"One MMR dose", "vax_one_mmr"),
        (r"Two MMR doses", "vax_two_mmr"),
    ]:
        m = re.search(rf"{label}:\s*(\d+)%", text)
        if m:
            data[f"{key}_pct"] = int(m.group(1))

    # Total hospitalized — "12% of cases hospitalized (202 of 1648)"
    m = re.search(
        r"(\d+)%\s+of cases hospitalized\s*\((\d+)\s+of\s+([\d,]+)\)", text
    )
    if m:
        data["hosp_total_pct"] = int(m.group(1))
        data["hosp_total_n"] = int(m.group(2))

    # Hospitalizations by age — compact: "Under 5 years: 22% (97 of 440)"
    for label, key in [
        (r"Under 5 years", "hosp_under5"),
        (r"5-19 years", "hosp_5_19"),
        (r"20\+ years", "hosp_20plus"),
        (r"Age unknown", "hosp_unknown"),
    ]:
        # Find in the hospitalization section (after "Percent of Age Group")
        pattern = rf"Percent of Age Group.*?{label}:\s*(\d+)%\s*\((\d+)\s+of\s+([\d,]+)\)"
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if m:
            data[f"{key}_pct"] = int(m.group(1))
            data[f"{key}_n"] = int(m.group(2))

    return data


def parse_two_column(text):
    """Parse the 2026 two-column format (2026 + 2025 comparison).
    Returns data for the CURRENT year (first column)."""
    data = {}
    lines = text.splitlines()

    # Find the structured table section starting with "Total Cases"
    total_idx = None
    for i, line in enumerate(lines):
        if re.match(r"Total Cases", line.strip(), re.IGNORECASE):
            total_idx = i
            break

    if total_idx is None:
        return data

    # After "Total Cases", the next non-empty line is the current year total
    # Stop if we hit a section label (Age, Vaccination, etc.)
    nums_after_total = []
    for line in lines[total_idx + 1:]:
        stripped = line.strip()
        if stripped and re.match(r"(Age|Vaccination|U\.S\.|Percent)", stripped):
            break
        if stripped and re.match(r"[\d,]+$", stripped):
            nums_after_total.append(int(stripped.replace(",", "")))
            if len(nums_after_total) == 2:
                break

    if nums_after_total:
        data["total_cases_override"] = nums_after_total[0]

    # Age groups — multi-line format
    # Pattern: "Under 5 years" then on a later line "278 (24%)"
    age_section = text[text.lower().find("age\n"):]  if "Age\n" in text else text
    for label, key in [
        ("Under 5 years", "age_under5"),
        ("5-19 years", "age_5_19"),
        (r"20\+ years", "age_20plus"),
        ("Age unknown", "age_unknown"),
    ]:
        # Find the label, then grab the FIRST "N (P%)" after it
        pattern = rf"{label}\s*\n\s*\n?\s*([\d,]+)\s*\((\d+)%\)"
        m = re.search(pattern, age_section)
        if m:
            data[f"{key}_n"] = int(m.group(1).replace(",", ""))
            data[f"{key}_pct"] = int(m.group(2))

    # Vaccination status — multi-line format
    vax_section = text[text.lower().find("vaccination status"):]
    for label, key in [
        ("Unvaccinated or Unknown", "vax_unvax_or_unknown"),
        ("One MMR dose", "vax_one_mmr"),
        ("Two MMR doses", "vax_two_mmr"),
    ]:
        pattern = rf"{label}\s*\n\s*\n?\s*(\d+)%"
        m = re.search(pattern, vax_section)
        if m:
            data[f"{key}_pct"] = int(m.group(1))

    # Total hospitalized — "5%\n\n(58 of 1136 cases)"
    hosp_section = text[text.lower().find("total hospitalized"):]
    m = re.search(r"Total Hospitalized\s*\n\s*\n?\s*(\d+)%\s*\n\s*\n?\s*\((\d+)\s+of\s+([\d,]+)\s+cases\)", hosp_section, re.IGNORECASE)
    if m:
        data["hosp_total_pct"] = int(m.group(1))
        data["hosp_total_n"] = int(m.group(2))

    # Hospitalizations by age — "7% (20 of 278)"
    hosp_age_section = text[text.lower().find("percent of age group hospitalized"):]
    for label, key in [
        ("Under 5 years", "hosp_under5"),
        ("5-19 years", "hosp_5_19"),
        (r"20\+ years", "hosp_20plus"),
        ("Age unknown", "hosp_unknown"),
    ]:
        pattern = rf"{label}\s*\n\s*\n?\s*(\d+)%\s*\((\d+)\s+of\s+([\d,]+)\)"
        m = re.search(pattern, hosp_age_section)
        if m:
            data[f"{key}_pct"] = int(m.group(1))
            data[f"{key}_n"] = int(m.group(2))

    return data


def is_two_column_format(text):
    """Detect whether this is the 2026 two-column format."""
    return "Total Cases" in text and "To date" in text


def parse_file(filepath):
    """Parse a single raw text file and return a dict of extracted fields."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    ts = os.path.basename(filepath).replace(".txt", "")
    snapshot_date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"

    update_date = parse_update_date(text)
    total_cases = parse_total_cases(text)

    if is_two_column_format(text):
        parsed = parse_two_column(text)
        # The two-column format has an explicit total in the table
        if "total_cases_override" in parsed:
            total_cases = parsed.pop("total_cases_override")
    else:
        parsed = parse_single_year(text)

    row = {
        "snapshot_date": snapshot_date,
        "update_date": update_date or "NA",
        "total_cases": total_cases if total_cases is not None else "NA",
    }

    # Age columns
    for key in ["age_under5", "age_5_19", "age_20plus", "age_unknown"]:
        row[f"{key}_n"] = parsed.get(f"{key}_n", "NA")
        row[f"{key}_pct"] = parsed.get(f"{key}_pct", "NA")

    # Vaccination columns
    for key in ["vax_unvax_or_unknown", "vax_one_mmr", "vax_two_mmr"]:
        row[f"{key}_pct"] = parsed.get(f"{key}_pct", "NA")

    # Hospitalization columns
    row["hosp_total_n"] = parsed.get("hosp_total_n", "NA")
    row["hosp_total_pct"] = parsed.get("hosp_total_pct", "NA")

    for key in ["hosp_under5", "hosp_5_19", "hosp_20plus", "hosp_unknown"]:
        row[f"{key}_n"] = parsed.get(f"{key}_n", "NA")
        row[f"{key}_pct"] = parsed.get(f"{key}_pct", "NA")

    return row


COLUMNS = [
    "snapshot_date",
    "update_date",
    "total_cases",
    "age_under5_n", "age_under5_pct",
    "age_5_19_n", "age_5_19_pct",
    "age_20plus_n", "age_20plus_pct",
    "age_unknown_n", "age_unknown_pct",
    "vax_unvax_or_unknown_pct",
    "vax_one_mmr_pct",
    "vax_two_mmr_pct",
    "hosp_total_n", "hosp_total_pct",
    "hosp_under5_n", "hosp_under5_pct",
    "hosp_5_19_n", "hosp_5_19_pct",
    "hosp_20plus_n", "hosp_20plus_pct",
    "hosp_unknown_n", "hosp_unknown_pct",
]


def main():
    txt_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.txt")))
    if not txt_files:
        print("No raw .txt files found in raw/ — run the scraper first.")
        return

    rows = []
    for filepath in txt_files:
        try:
            row = parse_file(filepath)
            rows.append(row)
        except Exception as e:
            print(f"  Error parsing {os.path.basename(filepath)}: {e}")

    # Sort by snapshot date
    rows.sort(key=lambda r: r["snapshot_date"])

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Parsed {len(rows)} files -> {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
