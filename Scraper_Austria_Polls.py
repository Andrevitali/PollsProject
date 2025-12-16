import requests
from bs4 import BeautifulSoup
import csv
import re

URL = "https://en.wikipedia.org/wiki/Next_Austrian_legislative_election"
RAW_OUTPUT = "Austria_national_polls_last5years_bs4.csv"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


def Scraper_Austria():
    resp = requests.get(URL, headers=headers)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    all_tables = soup.find_all("table", class_="wikitable")

    # Keep only tables that look like opinion poll tables
    poll_tables = []
    for table in all_tables:
        first_tr = table.find("tr")
        if not first_tr:
            continue
        header_cells = [th.get_text(" ", strip=True) for th in first_tr.find_all("th")]
        header_joined = " ".join(header_cells)
        if "Fieldwork date" in header_joined and "Lead" in header_joined:
            poll_tables.append(table)

    if not poll_tables:
        raise RuntimeError("No poll tables found (couldn't detect 'Fieldwork date' + 'Lead').")

    all_rows = []  # list of (year_int, [cell_texts])
    header = None
    n_header = None
    date_idx = None  # index of "Fieldwork date" in the full header

    for table in poll_tables:
        rows = table.find_all("tr")

        for tr in rows:
            ths = tr.find_all("th")
            tds = tr.find_all("td")

            # Header row (set once)
            if ths and header is None:
                header = [th.get_text(" ", strip=True) for th in ths]
                n_header = len(header)

                # Find "Fieldwork date" column index
                try:
                    date_idx = header.index("Fieldwork date")
                except ValueError:
                    # Fallback: sometimes header text differs slightly
                    date_idx = None
                continue  # don't treat header as data

            # Skip rows without data cells
            if not tds and not (ths and tds):
                continue

            # Build row from BOTH th + td (pollster is often in th)
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            cells_text = [c.get_text(" ", strip=True) for c in cells]

            # If we never found the date column name, try a best-effort guess:
            # Polling firm is usually col 0, so Fieldwork date often col 1
            idx = date_idx if date_idx is not None else 1
            if idx >= len(cells_text):
                continue

            date_text = cells_text[idx]
            if not date_text:
                continue

            # Extract year from the date text (e.g., "8–9 Dec 2025", "Early Sep 2025")
            m = re.search(r"(19|20)\d{2}", date_text)
            if not m:
                continue
            year = int(m.group(0))

            # Normalize length to match header (avoid parser errors later)
            if n_header is None:
                # Shouldn't happen, but safe fallback
                n_header = len(cells_text)
                header = [f"col_{i}" for i in range(n_header)]

            if len(cells_text) < n_header:
                cells_text += [""] * (n_header - len(cells_text))
            elif len(cells_text) > n_header:
                cells_text = cells_text[:n_header]

            all_rows.append((year, cells_text))

    if not all_rows:
        raise RuntimeError("No data rows found (year could not be extracted from Fieldwork date).")

    # Keep only last 5 distinct years
    years_found = sorted({y for y, _ in all_rows}, reverse=True)
    keep_years = set(years_found[:5])
    filtered_rows = [(y, cells) for (y, cells) in all_rows if y in keep_years]

    # Write CSV
    with open(RAW_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Year"] + header)
        for year, cells in filtered_rows:
            writer.writerow([year] + cells)

    print("Years found in poll tables:", years_found)
    print("Keeping years:", sorted(keep_years, reverse=True))
    print(f"✅ Saved {len(filtered_rows)} rows to {RAW_OUTPUT}")


def main():
    Scraper_Austria()


if __name__ == "__main__":
    main()
