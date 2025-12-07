import os
import pandas as pd
import altair as alt
from vega_datasets import data

# Dark Theme
dark_theme = {
    "background": "#000000",  # full black background
    "view": {"stroke": "transparent"},
    "axis": {
        "domainColor": "#ffffff",
        "labelColor": "#ffffff",
        "titleColor": "#ffffff",
        "gridColor": "#444444",
    },
    "legend": {
        "labelColor": "#ffffff",
        "titleColor": "#ffffff",
    },
    "title": {"color": "#ffffff"},
}

# Function for map: leading party colour from last 10 polls
def compute_leading_color(df: pd.DataFrame) -> str:
    """Colour of the leading party in the last 10 polls (by average share)."""
    df_sorted = df.sort_values("Date_conducted")
    last10 = df_sorted.tail(10).copy()

    party_cols = ["Lab", "Con", "Ref", "Grn", "LD", "SNP"]
    # Ensure numeric
    for col in party_cols:
        if col in last10.columns:
            last10[col] = pd.to_numeric(last10[col], errors="coerce")

    avg_last10 = last10[party_cols].mean(numeric_only=True)
    leading_party = avg_last10.idxmax()

    party_colors = {
        "Lab": "#E4003B",  # red
        "Con": "#0087DC",  # blue
        "Ref": "#12B6CF",  # turquoise
        "Grn": "#6AB023",  # green
        "LD":  "#FDBB30",  # orange
        "SNP": "#FFF95D",  # yellow
    }

    return party_colors.get(leading_party, "#E4003B")  # default to Labour red


#  Simple Europe map with UK highlighted
def make_uk_map(df: pd.DataFrame) -> alt.Chart:
    countries = alt.topo_feature(data.world_110m.url, "countries")
    leading_color = compute_leading_color(df)

    chart = (
        alt.Chart(countries)
        .transform_calculate(
            country="datum.properties.name"
        )
        .mark_geoshape(stroke="white", strokeWidth=0.4)
        .encode(
            color=alt.condition(
                "datum.id == 826",
                alt.value(leading_color),
                alt.value("#555555"),
            ),
            tooltip=alt.Tooltip("country:N", title="Country"),
        )
        .project(
            type="mercator",
            center=[-25, 62],          # centre on UK / Western Europe
            scale=500,                 # zoom in on Europe
            clipExtent=[[0, 0], [600, 380]],
        )
        .properties(
            width=700,
            height=400,
            title="European Polls (highlighted by leading party in the last 10 polls)",
        )
    )

    return chart


#  LOESS polling trends -
def make_chart(df: pd.DataFrame) -> alt.Chart:
    # Define parties their colours
    party_cols = ['Lab', 'Con', 'Ref', 'Grn', 'LD', 'SNP']
    party_colors = {
        'Lab': '#E4003B',   # red
        'Con': '#0087DC',   # blue
        'Ref': '#12B6CF',   # turquoise
        'Grn': '#6AB023',   # green
        'LD':  '#FDBB30',   # orange
        'SNP': '#FFF95D'    # yellow
    }

    # Explicit colour scale
    color_scale = alt.Scale(
        domain=['Lab', 'Con', 'Ref', 'Grn', 'LD', 'SNP'],
        range=['#E4003B', '#0087DC', '#12B6CF', '#6AB023', '#FDBB30', '#FFF95D']
    )

    # Ensure numeric types for party columns
    for col in party_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Base chart in long format
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
                legend=None,
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

    # LOESS lines layer (no legend)
    lines = (
        base
        .transform_loess(
            'Date_conducted',
            'Value',
            groupby=['Party']
        )
        .mark_line(size=3.5)
        .encode(
            x=alt.X('Date_conducted:T', title='Date Conducted'),
            y=alt.Y('Value:Q', title="Percentage"),
            color=alt.Color(
                'Party:N',
                scale=color_scale,
                legend=None,
            ),
            tooltip=[
                alt.Tooltip('Date_conducted:T', title='Date Conducted'),
                alt.Tooltip('Party:N', title='Party'),
                alt.Tooltip('Value:Q', title='Smoothed Value', format='.1f')
            ]
        )
    )

    # Title with last updated date
    last_date_str = pd.to_datetime(df['Date_conducted']).max().strftime('%d %b %Y')

    main_chart = (points + lines).properties(
        width=880,   # a bit wider so legend can sit close
        height=400,
        title=f"UK Polling Trends (LOESS) (Updated on {last_date_str})"
    )

    #Custom legend as a separate chart
    legend_order = ['Lab', 'Con', 'Ref', 'Grn', 'LD', 'SNP']
    legend_labels = {
        'Lab': 'Labour',
        'Con': 'Conservative',
        'Ref': 'Reform UK',
        'Grn': 'Green',
        'LD': 'Liberal Democrats',
        'SNP': 'SNP',
    }
    legend_df = pd.DataFrame({
        'Party': legend_order,
        'Label': [legend_labels[p] for p in legend_order],
    })

    # circles for legend
    legend_swatch = (
        alt.Chart(legend_df)
        .mark_circle(size=80)
        .encode(
            y=alt.Y(
                'Party:N',
                axis=None,
                sort=legend_order,
                scale=alt.Scale(padding=0.05),
            ),
            color=alt.Color('Party:N', scale=color_scale, legend=None),
        )
    )

    legend_text = (
        alt.Chart(legend_df)
        .mark_text(
            align='left',
            baseline='middle',
            dx=8
        )
        .encode(
            y=alt.Y(
                'Party:N',
                axis=None,
                sort=legend_order,
                scale=alt.Scale(padding=0.05),
            ),
            text='Label:N',
            color=alt.value("white"),
        )
    )

    legend_chart = (
        (legend_swatch + legend_text)
        .properties(
            width=150,
            height=100,
            title="Party:",
        )
    )



    chart_with_legend = alt.hconcat(main_chart, legend_chart, spacing=3)

    return chart_with_legend



# Latest 10 polls table
def make_latest_polls_table(df: pd.DataFrame) -> alt.Chart:
    # Sort by date and keep latest 10 polls
    df_sorted = df.sort_values("Date_conducted", ascending=False).copy()
    last5 = df_sorted.head(10).copy()

    # Format date
    last5["Date"] = last5["Date_conducted"].dt.strftime("%d %b %Y")
    last5["Sample Size"] = last5["Sample_size"]

    # Party columns & colours
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
    cols = ["Date"] + party_cols + ["Lead", "Pollster", "Sample Size"]
    available_cols = [c for c in cols if c in last5.columns]

    # Find leading party per row
    max_party_list = []
    max_color_list = []

    for _, row in last5.iterrows():
        best_party = None
        best_val = None

        for col in party_cols:
            val = row[col]
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
    # for zebra striping
    table_df["row_is_even"] = (table_df.index % 2 == 0).astype(int)

    # Melt to long format: one row per cell
    cell_df = table_df.melt(
        id_vars=["row", "max_party", "max_color", "row_is_even"],
        value_vars=available_cols,
        var_name="column",
        value_name="value",
    )

    # Background striping layer
    stripe_bg = (
        alt.Chart(cell_df)
        .mark_rect()
        .encode(
            x=alt.X("column:N", title=None, sort=available_cols),
            y=alt.Y("row:O", axis=None),
            color=alt.condition(
                "datum.row_is_even == 1",
                alt.value("#111111"),    # slightly lighter than pure black
                alt.value("#000000"),
            )
        )
        .properties(width=1000, height=200)
    )

    # --- base text layers: split numeric vs non-numeric for alignment ---
    numeric_columns = party_cols + ["Sample Size"]

    # non-numeric: Date, Lead, Pollster -> left aligned
    base_text_non_numeric = (
        alt.Chart(cell_df)
        .transform_filter(
            "indexof(['Date','Lead','Pollster'], datum.column) >= 0"
        )
        .mark_text(align="center", dx=3, dy=3, fontSize=11)
        .encode(
            x=alt.X("column:N", title=None, sort=available_cols),
            y=alt.Y("row:O", axis=None),
            text=alt.Text("value:N"),
            color=alt.value("white"),
        )
    )

    # numeric: party percentages + sample size -> right aligned
    base_text_numeric = (
        alt.Chart(cell_df)
        .transform_filter(
            f"indexof({numeric_columns}, datum.column) >= 0"
        )
        .mark_text(align="center", dx=-3, dy=3, fontSize=13)
        .encode(
            x=alt.X("column:N", title=None, sort=available_cols),
            y=alt.Y("row:O", axis=None),
            text=alt.Text("value:N"),
            color=alt.value("white"),
        )
    )

    base = base_text_non_numeric + base_text_numeric

    # Highlight layer: leading party cell (numeric, right-aligned)
    highlight = (
        alt.Chart(cell_df)
        .transform_filter("datum.column === datum.max_party")
        .mark_text(align="center", dx=-3, dy=3, fontSize=13, fontWeight="bold")
        .encode(
            x=alt.X("column:N", title=None, sort=available_cols),
            y=alt.Y("row:O", axis=None),
            text=alt.Text("value:N"),
            color=alt.Color("max_color:N", scale=None),
        )
    )

    # Highlight layer: Lead column (text, left-aligned)
    lead_highlight = (
        alt.Chart(cell_df)
        .transform_filter("datum.column === 'Lead'")
        .mark_text(align="center", dx=3, dy=3, fontSize=13, fontWeight="bold")
        .encode(
            x=alt.X("column:N", title=None, sort=available_cols),
            y=alt.Y("row:O", axis=None),
            text=alt.Text("value:N"),
            color=alt.Color("max_color:N", scale=None),
        )
    )

    table_chart = (
        (stripe_bg + base + highlight + lead_highlight)
        .properties(
            width=1000,
            height=200,
            title="Latest 10 polls (leading party highlighted)",
        )
    )

    return table_chart




#  Main
def main():
    # Load data
    df = pd.read_csv("Uk_polls_clean.csv")
    df["Date_conducted"] = pd.to_datetime(df["Date_conducted"])

    # Build components
    uk_map = make_uk_map(df)
    chart = make_chart(df)   # now includes its own legend on the right
    table = make_latest_polls_table(df)

    # Layout: map on top, chart (with legend) and table below
    combined = (uk_map & chart & table).configure(**dark_theme)

    os.makedirs("dashboard", exist_ok=True)
    out_path = os.path.join("dashboard", "index.html")

    combined.save(out_path)
    print(f"✅ Dashboard saved to {out_path}")


if __name__ == "__main__":
    main()
