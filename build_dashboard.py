import os
import re
import warnings
import pandas as pd
import altair as alt
from datetime import datetime
from vega_datasets import data

# Silence Altair harmless warning
warnings.filterwarnings(
    "ignore",
    message="Automatically deduplicated selection parameter with identical configuration.*",
    category=UserWarning,
)

# -------------------------------------------------------------------
# Dark Theme
# -------------------------------------------------------------------
dark_theme = {
    "background": "#000000",
    "view": {"stroke": "transparent"},
    "axis": {
        "domainColor": "#ffffff",
        "labelColor": "#ffffff",
        "titleColor": "#ffffff",
        "gridColor": "#444444",
    },
    "legend": {"labelColor": "#ffffff", "titleColor": "#ffffff"},
    "title": {"color": "#ffffff"},
}

# -------------------------------------------------------------------
# Party colours (optional)
# -------------------------------------------------------------------
KNOWN_PARTY_COLORS = {
    # UK
    "Lab": "#E4003B",
    "Con": "#0087DC",
    "Ref": "#12B6CF",
    "Grn": "#6AB023",
    "LD":  "#FDBB30",
    "SNP": "#FFF95D",
    # IT
    "FdI": "#2D4EA2",
    "PD":  "#D40000",
    "M5S": "#F7D117",
    "Lega": "#00A859",
    "FI":  "#009FE3",
    "A":   "#7F7FFF",
    "IV":  "#F5A623",
    "AVS": "darkred",
    "+E":  "#9AD0F5",
    "NM":  "#BBBBBB",
}

AUTO_PALETTE = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC949", "#AF7AA1", "#FF9DA7", "#9C755F", "#BAB0AC",
    "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
    "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
]

def build_party_color_map(parties: list[str]) -> dict[str, str]:
    parties_sorted = sorted(parties)
    out, i = {}, 0
    for p in parties_sorted:
        if p in KNOWN_PARTY_COLORS:
            out[p] = KNOWN_PARTY_COLORS[p]
        else:
            out[p] = AUTO_PALETTE[i % len(AUTO_PALETTE)]
            i += 1
    return out

# -------------------------------------------------------------------
# Party display names (legend + tooltips)
# -------------------------------------------------------------------
PARTY_LABELS = {
    # UK
    "Lab": "Labour",
    "Con": "Conservative",
    "Ref": "Reform UK",
    "Grn": "Green Party",
    "LD":  "Liberal Democrats",
    "SNP": "Scottish National Party",
    # IT
    "FdI": "Brothers of Italy",
    "PD":  "Democratic Party",
    "M5S": "Five Star Movement",
    "Lega": "Lega",
    "FI":  "Forza Italia",
    "A":   "Azione",
    "IV":  "Italia Viva",
    "AVS": "Green and Left Alliance",
    "+E":  "More Europe",
    "NM":  "Noi Moderati",
}

PARTY_LABELS_DF = pd.DataFrame(
    {"Party": list(PARTY_LABELS.keys()), "Party_full": list(PARTY_LABELS.values())}
)

# -------------------------------------------------------------------
# Long-format conversion (adds poll_id so "latest 10 polls" is well-defined)
# -------------------------------------------------------------------
def to_long_format(df_wide: pd.DataFrame, country_name: str, id_str: str, party_cols: list[str]) -> pd.DataFrame:
    d = df_wide.copy()
    d["country_name"] = country_name
    d["id_str"] = str(id_str)

    d["Date_conducted"] = pd.to_datetime(d["Date_conducted"], errors="coerce")
    d = d.dropna(subset=["Date_conducted"])

    # Ensure meta columns exist + are stringy where needed
    if "Pollster" not in d.columns:
        d["Pollster"] = ""
    d["Pollster"] = d["Pollster"].fillna("").astype(str)

    if "Sample_size" not in d.columns:
        d["Sample_size"] = None

    if "Lead" not in d.columns:
        d["Lead"] = ""
    d["Lead"] = d["Lead"].fillna("").astype(str)

    # stable poll id per row (per country file)
    d = d.reset_index(drop=True)
    d["poll_id"] = d.index.astype(int)

    # party columns: do NOT include Lead
    party_cols = [c for c in party_cols if c in d.columns and c != "Lead"]

    id_vars = ["country_name", "id_str", "poll_id", "Date_conducted", "Pollster", "Sample_size", "Lead"]

    long_df = d.melt(
        id_vars=id_vars,
        value_vars=party_cols,
        var_name="Party",
        value_name="Value",
    )
    long_df["Value"] = pd.to_numeric(long_df["Value"], errors="coerce")
    long_df = long_df.dropna(subset=["Value"])
    return long_df

# -------------------------------------------------------------------
# Map leading party (last 10 polls, mean)
# -------------------------------------------------------------------
def compute_leading_by_country_long(df_long: pd.DataFrame, color_map: dict[str, str]) -> pd.DataFrame:
    d = df_long.sort_values("Date_conducted")
    last10 = d.groupby("id_str", group_keys=False).tail(10)

    avg = (
        last10.groupby(["id_str", "Party"], as_index=False)["Value"]
        .mean()
        .rename(columns={"Value": "avg_value"})
    )

    idx = avg.groupby("id_str")["avg_value"].idxmax()
    lead = avg.loc[idx, ["id_str", "Party"]].rename(columns={"Party": "leading_party"})

    names = d[["id_str", "country_name"]].drop_duplicates()
    lead = lead.merge(names, on="id_str", how="left")
    lead["leading_color"] = lead["leading_party"].map(color_map)
    return lead

# -------------------------------------------------------------------
# Map
# -------------------------------------------------------------------
def make_map(lead_df: pd.DataFrame, country_sel) -> alt.Chart:
    countries = alt.topo_feature(data.world_110m.url, "countries")
    now_str = datetime.now().strftime("%d %b %Y at %H:%M")

    base = (
        alt.Chart(countries)
        .transform_calculate(id_str="toString(datum.id)")
        .transform_lookup(
            lookup="id_str",
            from_=alt.LookupData(lead_df, "id_str", ["country_name", "leading_party", "leading_color"]),
        )
        .mark_geoshape(stroke="white", strokeWidth=0.4)
        .encode(
            color=alt.condition(
                "isValid(datum.leading_color)",
                alt.Color("leading_color:N", scale=None),
                alt.value("#555555"),
            ),
            opacity=alt.condition(country_sel, alt.value(1.0), alt.value(0.85)),
            tooltip=[
                alt.Tooltip("country_name:N", title="Country"),
                alt.Tooltip("leading_party:N", title="Leading party"),
            ],
        )
        .project(
            type="mercator",
            center=[-25, 62],
            scale=500,
            clipExtent=[[0, 0], [600, 380]],
        )
        .properties(
            width=700,
            height=400,
            title={
                "text": "European Political Trends",
                "subtitle": f"Last updated on {now_str}",
                "fontSize": 16,
                "subtitleFontSize": 12,
                "subtitleColor": "white",
            },
        )
    )

    hint = (
        alt.Chart(pd.DataFrame({"text": ["Click a country to show its polls"]}))
        .mark_text(align="left", baseline="bottom", fontSize=13, fontWeight="bold")
        .encode(
            x=alt.value(20),
            y=alt.value(40),
            text="text:N",
            color=alt.value("gold"),

        )
    )

    return base + hint

# -------------------------------------------------------------------
# Chart + custom legend + last poll line (full party labels)
# -------------------------------------------------------------------
def make_chart_with_legend(
    df_long: pd.DataFrame,
    df_last_poll: pd.DataFrame,
    country_sel,
    color_map: dict[str, str]
) -> alt.Chart:
    party_list = sorted(df_long["Party"].dropna().unique().tolist())
    color_scale = alt.Scale(domain=party_list, range=[color_map[p] for p in party_list])

    # Add Party_full via lookup for tooltips + legend labels
    base = (
        alt.Chart(df_long)
        .transform_filter("length(data('country_sel_store')) > 0")
        .transform_filter(country_sel)
        .transform_lookup(
            lookup="Party",
            from_=alt.LookupData(PARTY_LABELS_DF, "Party", ["Party_full"])
        )
        .transform_calculate(
            Party_full="isValid(datum.Party_full) ? datum.Party_full : datum.Party"
        )
    )

    points = base.mark_point(opacity=0.4, filled=True).encode(
        x=alt.X("Date_conducted:T", axis=alt.Axis(format="%b-%y", labelAngle=0)),
        y=alt.Y("Value:Q", title="Percentage"),
        color=alt.Color("Party:N", scale=color_scale, legend=None),
        tooltip=[
            alt.Tooltip("country_name:N", title="Country"),
            alt.Tooltip("Date_conducted:T", title="Date", format="%d %b %Y"),
            alt.Tooltip("Party_full:N", title="Party"),
            alt.Tooltip("Value:Q", title="Value", format=".1f"),
            alt.Tooltip("Pollster:N", title="Pollster"),
            alt.Tooltip("Sample_size:Q", title="Sample Size"),
            alt.Tooltip("Lead:N", title="Lead"),
        ],
    )

    lines = (
        base
        .transform_loess("Date_conducted", "Value", groupby=["Party"])
        .mark_line(size=3.5)
        .encode(
            x=alt.X("Date_conducted:T", title="Date Conducted"),
            y=alt.Y("Value:Q", title="Percentage"),
            color=alt.Color("Party:N", scale=color_scale, legend=None),
            tooltip=[
                alt.Tooltip("Party_full:N", title="Party"),
                alt.Tooltip("Date_conducted:T", title="Date", format="%d %b %Y"),
                alt.Tooltip("Value:Q", title="Smoothed", format=".1f"),
            ],
        )
    )

    main_chart = (points + lines).properties(
        width=880,
        height=400,
        title={
            "text": "Polls and Trends (LOESS)",
            "subtitle": "(hover on the chart for more details)",
            "fontSize": 16,
            "subtitleColor": "white",
            "subtitleFontSize": 12,
        },
    )

    # Country label
    country_label = (
        alt.Chart(df_long)
        .transform_filter("length(data('country_sel_store')) > 0")
        .transform_filter(country_sel)
        .transform_aggregate(country_name="max(country_name)")
        .mark_text(align="center", baseline="top", fontSize=16, fontWeight="bold")
        .encode(
            x=alt.value(450),
            y=alt.value(10),
            text="country_name:N",
            color=alt.value("white"),
        )
    )

    # Last poll line (precomputed in pandas)
    last_poll_label = (
        alt.Chart(df_last_poll)
        .transform_filter("length(data('country_sel_store')) > 0")
        .transform_filter(country_sel)
        .mark_text(align="center", baseline="top", fontSize=12)
        .encode(
            x=alt.value(450),
            y=alt.value(30),
            text="last_line:N",
            color=alt.value("#dddddd"),
        )
    )

    # Legend base: compute max per Party, then attach Party_full for display
    legend_base = (
        alt.Chart(df_long)
        .transform_filter("length(data('country_sel_store')) > 0")
        .transform_filter(country_sel)
        .transform_aggregate(max_value="max(Value)", groupby=["Party"])
        .transform_lookup(
            lookup="Party",
            from_=alt.LookupData(PARTY_LABELS_DF, "Party", ["Party_full"])
        )
        .transform_calculate(
            Party_full="isValid(datum.Party_full) ? datum.Party_full : datum.Party"
        )
        .transform_filter("isValid(datum.max_value)")
    )
    sort_by_strength = alt.SortField("max_value", order="descending")

    legend_swatch = legend_base.mark_circle(size=80).encode(
        y=alt.Y("Party_full:N", axis=None, sort=sort_by_strength, scale=alt.Scale(padding=0.05)),
        color=alt.Color("Party:N", scale=color_scale, legend=None),
    )
    legend_text = legend_base.mark_text(align="left", baseline="middle", dx=8).encode(
        y=alt.Y("Party_full:N", axis=None, sort=sort_by_strength, scale=alt.Scale(padding=0.05)),
        text="Party_full:N",
        color=alt.value("white"),
    )

    # a bit wider to fit full names
    legend_chart = (legend_swatch + legend_text).properties(width=260, height=150, title="Party:")

    return alt.hconcat((main_chart + country_label + last_poll_label), legend_chart, spacing=10)

# -------------------------------------------------------------------
# Table (Date | parties | Lead | Pollster | Sample) + highlight winner cell
# -------------------------------------------------------------------
def build_wide_table_frames(df_long: pd.DataFrame, color_map: dict, top_polls: int = 10):
    """
    Table layout:
      Date | (Party columns...) | Lead | Pollster | Sample
    Returns:
      cells_df: id_str, row, col, text, text_color, font_weight
      grid_df:  id_str, row, col, row_is_even, is_header
    """

    # party ordering per country (max value across all time)
    party_strength = (
        df_long.groupby(["id_str", "Party"], as_index=False)["Value"]
        .max()
        .rename(columns={"Value": "maxv"})
        .sort_values(["id_str", "maxv"], ascending=[True, False])
    )
    party_strength["party_rank"] = party_strength.groupby("id_str").cumcount() + 1
    # Party columns start at col=1 (col=0 is Date)
    party_strength["col"] = party_strength["party_rank"]  # 1..K

    # latest polls per country (one row per poll)
    polls = (
        df_long[["id_str", "poll_id", "Date_conducted", "Pollster", "Sample_size", "Lead"]]
        .drop_duplicates(subset=["id_str", "poll_id"])
        .sort_values(["id_str", "Date_conducted"], ascending=[True, False])
        .copy()
    )
    polls["row"] = polls.groupby("id_str").cumcount() + 1
    polls = polls[polls["row"] <= top_polls].copy()

    polls["Date"] = polls["Date_conducted"].dt.strftime("%d %b %Y")
    polls["Sample"] = polls["Sample_size"]

    # row winner (max party by Value) for each poll
    winners = (
        df_long.merge(polls[["id_str", "poll_id"]], on=["id_str", "poll_id"], how="inner")
        .sort_values(["id_str", "poll_id", "Value"], ascending=[True, True, False])
        .groupby(["id_str", "poll_id"], as_index=False)
        .first()[["id_str", "poll_id", "Party"]]
        .rename(columns={"Party": "max_party"})
    )
    polls = polls.merge(winners, on=["id_str", "poll_id"], how="left")
    polls["max_color"] = polls["max_party"].map(color_map).fillna("white")

    # Lead formatting (fix decimals)
    def _fmt_lead(x):
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return ""
        s = str(x).strip()
        if s == "" or s.lower() == "nan":
            return ""
        s = s.replace(",", ".")
        # numeric direct
        try:
            xf = float(s)
            return str(int(xf)) if xf.is_integer() else str(xf).rstrip("0").rstrip(".")
        except Exception:
            pass
        # extract numeric substring anywhere
        m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
        if m:
            num = m.group(0)
            try:
                xf = float(num)
                return str(int(xf)) if xf.is_integer() else str(xf).rstrip("0").rstrip(".")
            except Exception:
                return num
        return s

    header_rows = []
    meta_cells = []
    party_cells_records = []

    for cid in polls["id_str"].unique():
        ps = party_strength[party_strength["id_str"] == cid].copy()
        max_party_col = int(ps["col"].max()) if len(ps) else 0

        # meta columns AFTER parties
        lead_col = max_party_col + 1
        pollster_col = max_party_col + 2
        sample_col = max_party_col + 3

        # header row (row 0)
        header_rows.append({"id_str": cid, "row": 0, "col": 0, "text": "Date", "text_color": "white", "font_weight": "bold"})
        for _, r in ps.iterrows():
            header_rows.append({"id_str": cid, "row": 0, "col": int(r["col"]), "text": r["Party"], "text_color": "white", "font_weight": "bold"})
        header_rows.append({"id_str": cid, "row": 0, "col": lead_col, "text": "Lead", "text_color": "white", "font_weight": "bold"})
        header_rows.append({"id_str": cid, "row": 0, "col": pollster_col, "text": "Pollster", "text_color": "white", "font_weight": "bold"})
        header_rows.append({"id_str": cid, "row": 0, "col": sample_col, "text": "Sample", "text_color": "white", "font_weight": "bold"})

        # body meta cells
        p_country = polls[polls["id_str"] == cid].copy()
        for _, r in p_country.iterrows():
            row = int(r["row"])
            max_color = r.get("max_color", "white")

            meta_cells.append({"id_str": cid, "row": row, "col": 0, "text": str(r.get("Date", "")), "text_color": "white", "font_weight": "normal"})
            lead_text = _fmt_lead(r.get("Lead", ""))
            meta_cells.append({"id_str": cid, "row": row, "col": lead_col, "text": lead_text, "text_color": max_color, "font_weight": "bold" if lead_text.strip() else "normal"})
            meta_cells.append({"id_str": cid, "row": row, "col": pollster_col, "text": str(r.get("Pollster", "")), "text_color": "white", "font_weight": "normal"})
            sample = r.get("Sample")
            meta_cells.append({"id_str": cid, "row": row, "col": sample_col, "text": "" if pd.isna(sample) else str(int(sample)), "text_color": "white", "font_weight": "normal"})

        # party cells for this country
        df_body = (
            df_long.merge(
                p_country[["id_str", "poll_id", "row", "max_party", "max_color"]],
                on=["id_str", "poll_id"],
                how="inner",
            )
            .merge(ps[["Party", "col"]], on="Party", how="left")
            .dropna(subset=["col"])
            .copy()
        )

        df_body["row"] = df_body["row"].astype(int)
        df_body["col"] = df_body["col"].astype(int)
        df_body["text"] = df_body["Value"].round(0).astype(int).astype(str)

        is_win = df_body["Party"] == df_body["max_party"]
        df_body["text_color"] = "white"
        df_body.loc[is_win, "text_color"] = df_body.loc[is_win, "max_color"]
        df_body["font_weight"] = "normal"
        df_body.loc[is_win, "font_weight"] = "bold"

        party_cells_records.extend(
            df_body[["id_str", "row", "col", "text", "text_color", "font_weight"]].to_dict("records")
        )

    cells_df = pd.DataFrame(header_rows + meta_cells + party_cells_records)

    # grid for stripes (per country, only its columns)
    grid_rows = []
    for cid in polls["id_str"].unique():
        ps = party_strength[party_strength["id_str"] == cid]
        max_party_col = int(ps["col"].max()) if len(ps) else 0
        lead_col = max_party_col + 1
        pollster_col = max_party_col + 2
        sample_col = max_party_col + 3

        cols = [0] + ps["col"].astype(int).tolist() + [lead_col, pollster_col, sample_col]
        cols = sorted(set(cols))

        for row in range(0, top_polls + 1):  # include header row 0
            for col in cols:
                grid_rows.append({
                    "id_str": cid,
                    "row": row,
                    "col": col,
                    "row_is_even": row % 2,
                    "is_header": row == 0
                })

    grid_df = pd.DataFrame(grid_rows)
    return cells_df, grid_df

def make_wide_table(cells_df: pd.DataFrame, grid_df: pd.DataFrame, country_sel) -> alt.Chart:
    g = grid_df.copy()
    g["bg"] = "#000000"
    g.loc[g["is_header"] == True, "bg"] = "#222222"
    g.loc[(g["is_header"] == False) & (g["row_is_even"] == 1), "bg"] = "#111111"

    stripes = (
        alt.Chart(g)
        .transform_filter("length(data('country_sel_store')) > 0")
        .transform_filter(country_sel)
        .mark_rect()
        .encode(
            x=alt.X("col:O", axis=None, sort="ascending"),
            y=alt.Y("row:O", axis=None, sort="ascending"),
            color=alt.Color("bg:N", scale=None),
        )
    )

    text_base = (
        alt.Chart(cells_df)
        .transform_filter("length(data('country_sel_store')) > 0")
        .transform_filter(country_sel)
        .encode(
            x=alt.X("col:O", axis=None, sort="ascending"),
            y=alt.Y("row:O", axis=None, sort="ascending"),
            text="text:N",
            color=alt.Color("text_color:N", scale=None),
        )
    )

    text_normal = text_base.transform_filter("datum.font_weight != 'bold'").mark_text(fontSize=13, dy=3)
    text_bold = text_base.transform_filter("datum.font_weight == 'bold'").mark_text(fontSize=15, dy=3, fontWeight="bold")
    text = text_normal + text_bold

    return (stripes + text).properties(
        width=1050,
        height=280,
        title={
            "text": "Latest 10 polls",
            "subtitle": "Leading party highlighted",
            "fontSize": 16,
            "subtitleColor": "white",
            "subtitleFontSize": 12,
        },
    )

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
def main():
    uk_wide = pd.read_csv("Uk_polls_clean.csv")
    it_wide = pd.read_csv("Italy_polls_clean.csv")

    UK_PARTIES = ["Lab", "Con", "Ref", "Grn", "LD", "SNP"]
    IT_PARTIES = ["FdI", "PD", "M5S", "Lega", "FI", "A", "IV", "AVS", "+E", "NM"]  # Lead is meta

    uk_long = to_long_format(uk_wide, "United Kingdom", "826", UK_PARTIES)
    it_long = to_long_format(it_wide, "Italy", "380", IT_PARTIES)
    df_long = pd.concat([uk_long, it_long], ignore_index=True)

    # ---- Color map + map leading party ----
    all_parties = sorted(df_long["Party"].dropna().unique().tolist())
    color_map = build_party_color_map(all_parties)
    lead_df = compute_leading_by_country_long(df_long, color_map)

    # ---- Last poll label per country (precomputed -> no NaN/0/NaN) ----
    df_polls_meta = (
        df_long[["country_name", "id_str", "poll_id", "Date_conducted", "Pollster"]]
        .drop_duplicates(subset=["id_str", "poll_id"])
        .copy()
    )
    df_polls_meta["Date_conducted"] = pd.to_datetime(df_polls_meta["Date_conducted"], errors="coerce")
    df_polls_meta["Pollster"] = df_polls_meta["Pollster"].fillna("").astype(str)

    df_last_poll = (
        df_polls_meta.sort_values(["id_str", "Date_conducted"], ascending=[True, False])
        .groupby("id_str", as_index=False)
        .head(1)
        .copy()
    )

    df_last_poll["last_date"] = df_last_poll["Date_conducted"].dt.strftime("%d %b %Y").fillna("Unknown date")
    df_last_poll["Pollster"] = df_last_poll["Pollster"].replace({"nan": ""}).fillna("")
    df_last_poll["last_line"] = "Last poll: " + df_last_poll["last_date"]

    # ---- Table frames ----
    cells_df, grid_df = build_wide_table_frames(df_long, color_map, top_polls=10)

    # ---- Selection ----
    country_sel = alt.selection_point(
        name="country_sel",
        fields=["id_str"],
        empty="none",
        on="click",
    )

    # ---- Build dashboard ----
    europe_map = make_map(lead_df, country_sel)
    chart = make_chart_with_legend(df_long, df_last_poll, country_sel, color_map)
    table = make_wide_table(cells_df, grid_df, country_sel)

    combined = (europe_map & chart & table).add_params(country_sel).configure(**dark_theme)

    os.makedirs("dashboard", exist_ok=True)
    out_path = os.path.join("dashboard", "index.html")
    combined.save(out_path)
    print(f"✅ Dashboard saved to {out_path}")

if __name__ == "__main__":
    main()
