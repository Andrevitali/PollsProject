import pandas as pd

RAW_INPUT = "Italy_national_polls_last5years_bs4.csv"     # from scraper
CLEAN_OUTPUT = "Italy_polls_clean.csv"         # used by dashboard

def clean_numeric(df, Num_cols):
    #function that cleans and convert the numeric columns in Int64
    df[Num_cols]= (df[Num_cols]
                               .astype(str)
                               .replace({",": "", "%": "", "–": "", "−": ""},regex=True)
                               .apply(lambda col: col.str.strip())
                               .apply(pd.to_numeric, errors="coerce")
                               .astype("float64"))
    return df
def data_cleaner():
    df=pd.read_csv(RAW_INPUT)
    df['Fieldwork date'] = pd.to_datetime(
        df['Fieldwork date'].str[-6:] + " " + df['Year'].astype(str),
        format="%d %b %Y",
        errors="coerce" #(in caso in cui qualcuno non venga riconosciuto come data, skippa e scrive NaT
    ) #date format more user friedly
    df.rename(columns={"Fieldwork date": "Date_conducted", "Sample size": "Sample_size", 'Polling firm':'Pollster'}, inplace=True)
    df=df.drop(columns=["Year",'Others'])
    Num_cols = ['Sample_size', 'FdI', 'PD', 'M5S', 'Lega',
                'FI', 'A', 'IV', 'AVS','+E','NM', 'Lead']

    df = clean_numeric(df, Num_cols) #call the clean_numeric function

    df.to_csv(CLEAN_OUTPUT, index=False)
    print(f"✅ Saved cleaned data to {CLEAN_OUTPUT}")

def main():
    data_cleaner()


if __name__ == "__main__":
    main()
