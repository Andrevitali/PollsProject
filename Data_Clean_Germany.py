import pandas as pd

RAW_INPUT = "Germany_national_polls_last5years_bs4.csv"     # from scraper
CLEAN_OUTPUT = "Germany_polls_clean.csv"         # used by dashboard

def clean_numeric(df, Num_cols):
    #function that cleans and convert the numeric columns in Int64
    df[Num_cols]= (df[Num_cols]
                               .astype(str)
                               .replace({",": "", "%": "", "–": "", "−": ""},regex=True)
                               .apply(lambda col: col.str.strip())
                               .apply(pd.to_numeric, errors="coerce")
                               .astype("Float64"))
    df["Sample_size"] = (
        pd.to_numeric(df["Sample_size"], errors="coerce")
        .round(0)
        .astype("Int64")
    )
    return df
def data_cleaner():
    df=pd.read_csv(RAW_INPUT)
    df = df.drop(columns=["Abs."], axis=1, errors="ignore")
    df['Pollster'] = df['Polling firm'].str.split("[").str[0].str.strip() #to get rid of the link
    df['Date(s) conducted'] = pd.to_datetime(
        df['Fieldwork date'].str[-11:-5] + " " + df['Year'].astype(str),
        format="%d %b %Y",
        errors="coerce" #(in caso in cui qualcuno non venga riconosciuto come data, skippa e scrive NaT
    ) #date format more user friedly
    df.rename(columns={"Date(s) conducted": "Date_conducted", "Sample size": "Sample_size"}, inplace=True)
    df=df.drop(columns=["Year","Polling firm","Fieldwork date"])
    Num_cols = ['Sample_size', 'Union', 'AfD', 'SPD', 'Grüne',
                'Linke', 'BSW', 'FDP', 'Others']

    df = clean_numeric(df, Num_cols) #call the clean_numeric function

    df.to_csv(CLEAN_OUTPUT, index=False)
    print(f"✅ Saved cleaned data to {CLEAN_OUTPUT}")

def main():
    data_cleaner()


if __name__ == "__main__":
    main()
