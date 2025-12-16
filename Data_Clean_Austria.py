import pandas as pd
import re

RAW_INPUT = "Austria_national_polls_last5years_bs4.csv"     # from scraper
CLEAN_OUTPUT = "Austria_polls_clean.csv"                    # used by dashboard

def clean_numeric(df, Num_cols):
    # ✅ only keep numeric cols that actually exist (prevents KeyError)
    Num_cols = [c for c in Num_cols if c in df.columns]

    df[Num_cols] = (
        df[Num_cols]
        .astype(str)
        .replace({",": "", "%": "", "–": "", "−": "",r"\?": ""}, regex=True)
        .apply(lambda col: col.str.strip())
        .apply(pd.to_numeric, errors="coerce")
        .astype("Float64")
    )

    # ✅ keep sample size as Int64 (if present)
    if "Sample_size" in df.columns:
        df["Sample_size"] = (
            pd.to_numeric(df["Sample_size"], errors="coerce")
            .round(0)
            .astype("Int64")
        )

    return df

def data_cleaner():
    df = pd.read_csv(RAW_INPUT)


    # ✅ safer split (treat [ as literal)
    df["Pollster"] = df["Polling firm"].astype(str).str.split("(", n=1).str[0].str.strip()


    # ✅ ROBUST: extract a "dd Mon" from Fieldwork date (works for ranges like "9–11 Dec")
    # We take the LAST match (end of fieldwork range is usually the right “conducted date”)
    def extract_day_month(s: str) -> str:
        if pd.isna(s):
            return ""
        s = str(s).strip()
        matches = re.findall(r"\b(\d{1,2}\s+[A-Za-z]{3})\b", s)
        return matches[-1] if matches else ""

    day_month = df["Fieldwork date"].apply(extract_day_month)

    df["Date(s) conducted"] = pd.to_datetime(
        day_month + " " + df["Year"].astype(str),
        format="%d %b %Y",
        errors="coerce",
    )

    df.rename(columns={"Date(s) conducted": "Date_conducted", "Sample size": "Sample_size"}, inplace=True)

    df = df.drop(columns=["Year","Polling firm","Fieldwork date","Method"], errors="ignore")


    Num_cols = ['Sample_size', 'FPÖ', 'ÖVP', 'SPÖ', 'NEOS',
                'Grüne', 'KPÖ', 'Others']

    df = clean_numeric(df, Num_cols)
    df=df.rename(columns={"Grüne": "Grüne_AT"})
    df = df[df["Sample_size"].notna()]
    df.to_csv(CLEAN_OUTPUT, index=False)
    print(f"✅ Saved cleaned data to {CLEAN_OUTPUT}")

def main():
    data_cleaner()

if __name__ == "__main__":
    main()
