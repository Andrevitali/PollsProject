import pandas as pd
import altair as alt
import os

#Create Dark Theme for our chart
dark_theme = {

            "background": "#000000",             # full black background
            "view": {"stroke": "transparent"},
            "axis": {
                "domainColor": "#ffffff",
                "labelColor": "#ffffff",
                "titleColor": "#ffffff",
                "gridColor": "#444444"
            },
            "legend": {
                "labelColor": "#ffffff",
                "titleColor": "#ffffff"
            },
            "title": {"color": "#ffffff"}
        }
def make_chart(df: pd.DataFrame) -> alt.Chart:
    # Define parties and their colours
    party_cols = ['Lab', 'Con', 'Ref', 'Grn', 'LD', 'SNP']
    party_colors = {
        'Lab': '#E4003B',   #  red
        'Con': '#0087DC',   #  blue
        'Ref': '#12B6CF',   #  turquoise
        'Grn': '#6AB023',   #  green
        'LD':  '#FDBB30',   # orange
        'SNP': '#FFF95D'    #yellow
    }
    color_scale = alt.Scale(
        domain=list(party_colors.keys()),
        range=list(party_colors.values())
    )

    # Ensure numeric types for party columns
    for col in party_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Base chart in long format (otherwise we can't do the the visualisation)
    base = (
        alt.Chart(df)
        .transform_fold(
            party_cols,
            as_=['Party', 'Value']   # Party = column name, Value = its numeric value
        )
    )

    # Points layer
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

    # LOESS lines layer
    lines = (
        base
        .transform_loess(
            'Date_conducted',
            'Value',
            groupby=['Party']        # groupby LOESS per party
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



    #  Title with last updated date
    last_date_str = pd.to_datetime(df['Date_conducted']).max().strftime('%d %b %Y')

    chart = (points + lines).properties(
        width=1000,
        height=800,
        title=f"UK Polling Trends (LOESS) — Last updated: {last_date_str}"
    )

    return chart

def make_latest_polls_table(df: pd.DataFrame) -> alt.Chart:
    # Sort by date and keep latest 10 polls
    df_sorted = df.sort_values("Date_conducted", ascending=False).copy()
    last5 = df_sorted.head(10).copy()

    # Format date
    last5["Date"] = last5["Date_conducted"].dt.strftime("%d %b %Y")
    last5["Sample Size"]=last5["Sample_size"]

    # Party columns & colours (same as before)
    all_party_cols = ["Lab", "Con", "Ref", "LD", "Grn", "SNP"]
    party_colors = {
        "Lab": "#E4003B",
        "Con": "#0087DC",
        "Ref": "#12B6CF",
        "LD":  "#FDBB30",
        "Grn": "#6AB023",
        "SNP": "#FFF95D",
    }

    # Keeps party columns that are in the df
    party_cols = [c for c in all_party_cols if c in last5.columns]

    # Columns to display in the table
    cols = ['Date']+party_cols+["Lead","Pollster","Sample Size"]
    available_cols = [c for c in cols if c in last5.columns]

    #  Find leading party per row
    max_party_list = []
    max_color_list = []

    for _, row in last5.iterrows():
        best_party = None
        best_val = None

        for col in party_cols:
            val = row[col]
            # Make each cell individually to numeric (we had a problem before)
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

    # Build table dataframe
    table_df = last5[available_cols + ["max_party", "max_color"]].reset_index(drop=True)
    table_df["row"] = table_df.index.astype(str)

    # Melt to long format: one row per cell
    cell_df = table_df.melt(
        id_vars=["row", "max_party", "max_color"],
        value_vars=available_cols,
        var_name="column",
        value_name="value",
    )

    # Base layer: all values in white, normal weight
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

    # Highlight layer: only leading party, bold + party colour
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

    # Combine layers
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
    # This is the main function of the program. First: Load the cleaned UK data
    df = pd.read_csv("Uk_polls_clean.csv")
    df["Date_conducted"] = pd.to_datetime(df["Date_conducted"])

    # Second: Call make_chart to Build the chart
    chart = make_chart(df)

    # Third: call the function to make the table
    table = make_latest_polls_table(df)

    # Fourth: Combine chart (top) and table (bottom)
    combined = (chart & table).configure(**dark_theme)

    #
    os.makedirs("dashboard", exist_ok=True)
    out_path = os.path.join("dashboard", "index.html")

    # Finally: Save HTML dashboard
    combined.save(out_path)
    print(f"✅ Dashboard saved to {out_path}")

if __name__ == "__main__":
    main()
