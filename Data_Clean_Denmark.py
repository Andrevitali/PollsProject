import pandas as pd
import re

RAW_INPUT = "Denmark_national_polls_last5years_bs4.csv"     # from scraper
CLEAN_OUTPUT = "Denmark_polls_clean.csv"                    # used by dashboard

def clean_numeric(df, Num_cols):
    # ✅ only keep numeric cols that actually exist (prevents KeyError)
    Num_cols = [c for c in Num_cols if c in df.columns]

    df[Num_cols] = (
        df[Num_cols]
        .astype(str)
        .replace({",": "", "%": "", "–": "", "−": ""}, regex=True)
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

    df = df.drop(columns=["Gov.","Opp.","Red","Blue"], axis=1, errors="ignore")

    # ✅ safer split (treat [ as literal)
    df["Pollster"] = df["Polling firm"].astype(str).str.split(r"\[").str[0].str.strip()

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

    df = df.drop(columns=["Year","Polling firm","Fieldwork date"], errors="ignore")
    df = df.dropna(subset=["Date_conducted"])

    Num_cols = ['Sample_size', 'A', 'V', 'M', 'F',
                'Æ', 'I', 'C', 'Ø', 'B', 'H', 'Å', 'O', 'Others']

    df = clean_numeric(df, Num_cols)
    df=df.rename(columns={"A": "Social Democrats", "V": "Venstre (Liberal Party)", "M": "The Moderates",
                       "F": "Socialist People’s Party", "Æ": "Denmark Democrats", "I": "Liberal Alliance",
                       "C": "Conservative People’s Party", "Ø": "Red–Green Alliance", "B": "Social Liberal Party",
                       "Å": "The Alternative", "O": "Danish People’s Party", "H": "Hard Line (Stram Kurs)"})
    df.to_csv(CLEAN_OUTPUT, index=False)
    print(f"✅ Saved cleaned data to {CLEAN_OUTPUT}")

def main():
    data_cleaner()

if __name__ == "__main__":
    main()
