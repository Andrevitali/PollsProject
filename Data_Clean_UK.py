import pandas as pd

RAW_INPUT = "UK_national_polls_last5years_bs4.csv"     # from scraper
CLEAN_OUTPUT = "Uk_polls_clean.csv"         # used by dashboard

def clean_numeric(df, Num_cols):
    df[Num_cols]= (df[Num_cols]
                               .astype(str)
                               .replace({",": "", "%": "", "–": "", "−": ""},regex=True)
                               .apply(lambda col: col.str.strip())
                               .apply(pd.to_numeric, errors="coerce")
                               .astype("Int64"))
    return df
def data_cleaner():
    df=pd.read_csv(RAW_INPUT)
    df=df.drop(columns=["Client"], axis=1)
    df['Pollster'] = df['Pollster'].str.split("[").str[0].str.strip()
    df['Date(s) conducted'] = pd.to_datetime(
        df['Date(s) conducted'].str[-6:] + " " + df['Year'].astype(str),
        format="%d %b %Y",
        # errors="coerce" (in caso in cui qualcuno non venga riconosciuto come data, skippa e scrive NaT
    )
    df.rename(columns={"Date(s) conducted": "Date_conducted", "Sample size": "Sample_size"}, inplace=True)
    df=df.drop(columns=["Year","Area"])
    Num_cols = ['Sample_size', 'Lab', 'Con', 'Ref', 'LD',
                'Grn', 'SNP', 'PC', 'Others', 'Lead']
    df[[col for col in Num_cols]] = (df[[col for col in Num_cols]]
                                     .astype(str)
                                     .replace({",": "", "%": "", "–": "", "−": ""}, regex=True)
                                     .apply(lambda col: col.str.strip())
                                     .apply(pd.to_numeric, errors="coerce")
                                     .astype("Int64"))
    df = clean_numeric(df, Num_cols)

    df.to_csv(CLEAN_OUTPUT, index=False)
    print(f"✅ Saved cleaned data to {CLEAN_OUTPUT}")

def main():
    data_cleaner()


if __name__ == "__main__":
    main()
