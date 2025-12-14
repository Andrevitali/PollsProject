import requests
from bs4 import BeautifulSoup
import csv
import re

URL = "https://en.wikipedia.org/wiki/Opinion_polling_for_the_2026_Danish_general_election"
RAW_OUTPUT = "Denmark_national_polls_last5years_bs4.csv"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


def Scraper_Denmark():
    resp = requests.get(URL, headers=headers)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    all_tables = soup.find_all("table", class_="wikitable")

    national_tables = []
    for table in all_tables:
        first_tr = table.find("tr")
        if not first_tr:
            continue

        header_cells = [th.get_text(" ", strip=True) for th in first_tr.find_all("th")]
        if not header_cells:
            continue

        national_tables.append(table)

    if not national_tables:
        raise RuntimeError("No national poll tables found.")

    all_rows = []  # list of (year_int, [cell_texts])
    header = None
    n_header = None

    # There are 2 header rows and you don't want the first one
    first_header_skipped = False

    def _extract_year_from_row(tr, cells_text):
        """
        Tries (in order):
          1) any element in the row with data-sort-value
          2) a span.sortkey (common on Wikipedia sortable tables)
          3) regex year from the row text
        """
        # 1) any data-sort-value in the row
        el = tr.find(attrs={"data-sort-value": True})
        if el:
            sort_val = el.get("data-sort-value", "")
            m = re.search(r"(19|20)\d{2}", sort_val)
            if m:
                return int(m.group(0))

        # 2) span.sortkey text
        sk = tr.find("span", class_="sortkey")
        if sk:
            sk_text = sk.get_text(" ", strip=True)
            m = re.search(r"(19|20)\d{2}", sk_text)
            if m:
                return int(m.group(0))

        # 3) fallback: year from row text
        row_text = " ".join(cells_text)
        m = re.search(r"(19|20)\d{2}", row_text)
        if m:
            return int(m.group(0))

        return None

    for table in national_tables[0:4]:
        rows = table.find_all("tr")

        for tr in rows:
            ths = tr.find_all("th")
            tds = tr.find_all("td")

            # --- header handling (skip first header row, keep second) ---
            if ths and header is None:
                if not first_header_skipped:
                    first_header_skipped = True
                    continue  # skip the first header row
                header = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
                n_header = len(header)
                continue  # do not treat header row as data

            # skip any other header-like rows
            if ths and not tds:
                continue

            # data row must have some cells
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue

            cells_text = [c.get_text(" ", strip=True) for c in cells]

            # if header still not set for any reason, create fallback
            if header is None:
                header = [f"col_{i}" for i in range(len(cells_text))]
                n_header = len(header)

            # extract year robustly
            year = _extract_year_from_row(tr, cells_text)
            if year is None:
                continue

            # OPTIONAL sanity check: require some date-ish content (prevents "Average" rows sometimes)
            # If you find this filters out good rows, remove it.
            if not any(ch.isdigit() for ch in cells_text[0]):
                # doesn't look like a date in first column
                pass

            # normalize length to match header
            if len(cells_text) < n_header:
                cells_text += [""] * (n_header - len(cells_text))
            elif len(cells_text) > n_header:
                cells_text = cells_text[:n_header]

            all_rows.append((year, cells_text))

    if not all_rows:
        raise RuntimeError("No data rows with year found after filtering. (Page may not have poll rows in the first 4 tables.)")

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

    print("Years found in national tables:", years_found)
    print("Keeping years:", sorted(keep_years, reverse=True))
    print(f"✅ Saved {len(filtered_rows)} rows to {RAW_OUTPUT}")


def main():
    Scraper_Denmark()


if __name__ == "__main__":
    main()
