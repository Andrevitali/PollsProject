import requests
from bs4 import BeautifulSoup
import csv

URL = "https://en.wikipedia.org/wiki/Opinion_polling_for_the_next_German_federal_election"
RAW_OUTPUT = "Germany_national_polls_last5years_bs4.csv"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


def Scraper_Germany():
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

        header_joined = " ".join(header_cells)

        # Find National poll tables that have Abs.
        if "Abs." in header_joined:
            national_tables.append(table)

    if not national_tables:
        raise RuntimeError("No national poll tables found.")

    all_rows = []          # list of (year_int, [cell_texts])
    header = None
    area_idx = None
    n_header = None

    for table in national_tables:
        rows = table.find_all("tr")

        for tr in rows:
            ths = tr.find_all("th")
            tds = tr.find_all("td")

            # header row (only once, from first table)
            if ths and header is None:
                header = [th.get_text(" ", strip=True) for th in ths]
                n_header = len(header)  # ✅ FIX: define n_header here

            if not tds:
                continue

            # ✅ FIX: avoid IndexError if row is short
            if len(tds) < 2:
                continue

            # first td is the date column (on this page you are using index 1)
            date_td = tds[1]
            sort_val = date_td.get("data-sort-value")

            # if no data-sort-value, skip row (usually not a poll row)
            if not sort_val or len(sort_val) < 4 or not sort_val[:4].isdigit():
                continue

            year = int(sort_val[:4])

            cells_text = [td.get_text(" ", strip=True) for td in tds]

            # ✅ FIX: if header was never detected, create a fallback header from first valid row
            if header is None:
                header = [f"col_{i}" for i in range(len(cells_text))]
                n_header = len(header)

            # ✅ FIX: date_text must match date_td index
            # (you used tds[1] for date, so use cells_text[1])
            date_text = cells_text[1] if len(cells_text) > 1 else ""
            if not date_text:
                continue

            # normalize length to match header (avoid parser errors later)
            if len(cells_text) < n_header:
                cells_text += [""] * (n_header - len(cells_text))
            elif len(cells_text) > n_header:
                cells_text = cells_text[:n_header]

            all_rows.append((year, cells_text))

    if not all_rows:
        raise RuntimeError("No data rows with data-sort-value year found after filtering.")

    # Keep only last 5 distinct years (as National Elections are held every 5 years max)
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
    Scraper_Germany()


if __name__ == "__main__":
    main()
