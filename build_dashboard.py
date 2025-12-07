import pandas as pd
import altair as alt
import os

# Dark theme config (same as notebook)
dark_theme = {

            "background": "#000000",             # full black background
            "view": {"stroke": "transparent"},   # remove chart border
            "axis": {
                "domainColor": "#ffffff",
                "labelColor": "#ffffff",
                "titleColor": "#ffffff",
                "gridColor": "#444444"           # subtle grey gridlines
            },
            "legend": {
                "labelColor": "#ffffff",
                "titleColor": "#ffffff"
            },
            "title": {"color": "#ffffff"}
        }
def make_chart(df: pd.DataFrame) -> alt.Chart:
    # 1. Define parties and colours
    party_cols = ['Lab', 'Con', 'Ref', 'Grn', 'LD', 'SNP']
    party_colors = {
        'Lab': '#E4003B',   # Labour red
        'Con': '#0087DC',   # Conservative blue
        'Ref': '#12B6CF',   # Reform turquoise
        'Grn': '#6AB023',   # Green Party green
        'LD':  '#FDBB30',   # Lib Dem orange/yellow
        'SNP': '#FFF95D'    # SNP yellow
    }
    color_scale = alt.Scale(
        domain=list(party_colors.keys()),
        range=list(party_colors.values())
    )

    # 2. Ensure numeric types for party columns
    for col in party_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 3. Base chart in long format
    base = (
        alt.Chart(df)
        .transform_fold(
            party_cols,
            as_=['Party', 'Value']   # Party = column name, Value = its numeric value
        )
    )

    # 4. Points layer
    points = (
        base
        .mark_point(opacity=0.5, filled=True)
        .encode(
            x=alt.X(
                'Date_conducted:T',
                axis=alt.Axis(format='%b-%y', labelAngle=0)
            ),
            y='Value:Q',
            color=alt.Color(
                'Party:N',
                scale=color_scale,
                legend=alt.Legend(
                    title="Party",
                    labelExpr=(
                        "({'Lab': 'Labour', "
                        "'Con': 'Conservative', "
                        "'Ref': 'Reform UK', "
                        "'Grn': 'Green', "
                        "'LD': 'Liberal Democrats', "
                        "'SNP': 'SNP'}[datum.label])"
                    )
                )
            ),
            tooltip=[
                alt.Tooltip('Date_conducted:T', title='Date'),
                alt.Tooltip('Party:N', title='Party'),
                alt.Tooltip('Value:Q', title='Value', format='.1f'),
                alt.Tooltip('Pollster:N', title='Pollster'),
                alt.Tooltip('Sample_size:Q', title='Sample Size', format='.1f')
            ]
        )
    )

    # 5. LOESS lines layer
    lines = (
        base
        .transform_loess(
            'Date_conducted',
            'Value',
            groupby=['Party']        # separate LOESS per party
        )
        .mark_line(size=3.5)
        .encode(
            x=alt.X('Date_conducted:T', title='Date Conducted'),
            y=alt.Y('Value:Q', title="Percentage"),
            color=alt.Color(
                'Party:N',
                scale=color_scale,
                legend=alt.Legend(
                    title="Party",
                    labelExpr=(
                        "({'Lab': 'Labour', "
                        "'Con': 'Conservative', "
                        "'Ref': 'Reform UK', "
                        "'Grn': 'Green', "
                        "'LD': 'Liberal Democrats', "
                        "'SNP': 'SNP'}[datum.label])"
                    )
                )
            ),
            tooltip=[
                alt.Tooltip('Date_conducted:T', title='Date Conducted'),
                alt.Tooltip('Party:N', title='Party'),
                alt.Tooltip('Value:Q', title='Smoothed Value', format='.1f')
            ]
        )
    )



    # 7. Title with last updated date
    last_date_str = pd.to_datetime(df['Date_conducted']).max().strftime('%d %b %Y')

    chart = (points + lines).properties(
        width=1000,
        height=800,
        title=f"UK Polling Trends (LOESS) — Last updated: {last_date_str}"
    )

    return chart

def make_latest_polls_table(df: pd.DataFrame) -> alt.Chart:
    # 1. Sort by date and keep latest 5 polls
    df_sorted = df.sort_values("Date_conducted", ascending=False).copy()
    last5 = df_sorted.head(10).copy()

    # 2. Nicely formatted date
    last5["Date"] = last5["Date_conducted"].dt.strftime("%d %b %Y")
    last5["Sample Size"]=last5["Sample_size"]

    # 3. Party columns & colours
    all_party_cols = ["Lab", "Con", "Ref", "LD", "Grn", "SNP"]
    party_colors = {
        "Lab": "#E4003B",   # Labour red
        "Con": "#0087DC",   # Conservative blue
        "Ref": "#12B6CF",   # Reform turquoise
        "LD":  "#FDBB30",   # Lib Dem orange/yellow
        "Grn": "#6AB023",   # Green Party green
        "SNP": "#FFF95D",   # SNP yellow
    }

    # Only keep party columns that actually exist in the df
    party_cols = [c for c in all_party_cols if c in last5.columns]

    # Columns to display in the table
    cols = ['Date']+party_cols+["Lead","Pollster","Sample Size"]
    available_cols = [c for c in cols if c in last5.columns]

    # 4. Find leading party per row (no idxmax, robust to weird values)
    max_party_list = []
    max_color_list = []

    for _, row in last5.iterrows():
        best_party = None
        best_val = None

        for col in party_cols:
            val = row[col]
            # Coerce each cell individually to numeric
            val_num = pd.to_numeric(val, errors="coerce")
            if pd.notna(val_num):
                if best_val is None or val_num > best_val:
                    best_val = val_num
                    best_party = col

        if best_party is not None:
            max_party_list.append(best_party)
            max_color_list.append(party_colors.get(best_party, "white"))
        else:
            max_party_list.append(None)
            max_color_list.append("white")

    last5["max_party"] = max_party_list
    last5["max_color"] = max_color_list

    # 5. Build table dataframe
    table_df = last5[available_cols + ["max_party", "max_color"]].reset_index(drop=True)
    table_df["row"] = table_df.index.astype(str)

    # 6. Melt to long format: one row per cell
    cell_df = table_df.melt(
        id_vars=["row", "max_party", "max_color"],
        value_vars=available_cols,
        var_name="column",
        value_name="value",
    )

    # 7. Base layer: all values in white, normal weight
    base = (
        alt.Chart(cell_df)
        .mark_text(align="left", dx=3, dy=3)
        .encode(
            x=alt.X("column:N", title=None, sort=available_cols),
            y=alt.Y("row:O", axis=None),
            text=alt.Text("value:N"),
            color=alt.value("white"),
        )
    )

    # 8. Highlight layer: only leading party, bold + party colour
    highlight = (
        alt.Chart(cell_df)
        .transform_filter("datum.column === datum.max_party")
        .mark_text(align="left", dx=3, dy=3, fontWeight="bold")
        .encode(
            x=alt.X("column:N", title=None, sort=available_cols),
            y=alt.Y("row:O", axis=None),
            text=alt.Text("value:N"),
            color=alt.Color("max_color:N", scale=None),
        )
    )

    # 9. Combine layers
    table_chart = (
        (base + highlight)
        .properties(
            width=1000,
            height=180,
            title="Latest 10 polls (leading party highlighted)",
        )
    )

    return table_chart


def main():
    # 1. Load the cleaned UK data
    df = pd.read_csv("Uk_polls_clean.csv")
    df["Date_conducted"] = pd.to_datetime(df["Date_conducted"])

    # 2. Build the chart
    chart = make_chart(df)

    # 3. Ensure output folder exists
    table = make_latest_polls_table(df)

    # 4. Combine chart (top) and table (bottom)
    combined = (chart & table).configure(**dark_theme)

    # 5. Ensure output folder exists
    os.makedirs("dashboard", exist_ok=True)
    out_path = os.path.join("dashboard", "index.html")

    # 6. Save HTML dashboard
    combined.save(out_path)
    print(f"✅ Dashboard saved to {out_path}")

if __name__ == "__main__":
    main()
