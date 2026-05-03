from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


DATA_PATH = Path("data/processed/ka1_he_studies_flows_with_indicators.csv")
OUTPUT_PATH = Path("dashboard/dist/index.html")


def fig_to_base64() -> str:
    buffer = BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format="png", dpi=180, bbox_inches="tight")
    plt.close()
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def img_tag(encoded: str, alt: str) -> str:
    return f'<img src="data:image/png;base64,{encoded}" alt="{alt}" loading="lazy">'


def top_destinations_chart(flows: pd.DataFrame) -> str:
    top = flows.groupby(["receiving_code", "receiving_country"], as_index=False)["flow_count"].sum()
    top = top.sort_values("flow_count", ascending=False).head(15).sort_values("flow_count")
    labels = top["receiving_code"] + " - " + top["receiving_country"]

    plt.figure(figsize=(9, 6))
    plt.barh(labels, top["flow_count"], color="#2f6f73")
    plt.xlabel("Participants")
    plt.title("Top Erasmus Study Destinations, 2022")
    return img_tag(fig_to_base64(), "Bar chart of top Erasmus study destinations in 2022")


def italy_luxembourg_chart(flows: pd.DataFrame) -> str:
    subset = flows.loc[flows["sending_code"].isin(["IT", "LU"])].copy()
    subset["rank"] = subset.groupby("sending_code")["flow_count"].rank(method="first", ascending=False)
    subset = subset.loc[subset["rank"].le(10)]
    subset["label"] = subset["sending_code"] + " to " + subset["receiving_code"]
    subset = subset.sort_values(["sending_code", "flow_count"])

    colors = subset["sending_code"].map({"IT": "#b44e5a", "LU": "#2f6f73"})
    plt.figure(figsize=(9, 6))
    plt.barh(subset["label"], subset["flow_count"], color=colors)
    plt.xlabel("Participants")
    plt.title("Italy and Luxembourg Destination Profiles")
    return img_tag(fig_to_base64(), "Bar chart comparing Italy and Luxembourg Erasmus destinations")


def scatter_chart(flows: pd.DataFrame) -> str:
    plot_df = flows.dropna(subset=["gdp_gap_usd_wb"]).copy()
    totals = plot_df.groupby("sending_code")["flow_count"].transform("sum")
    plot_df["flow_share_sender"] = plot_df["flow_count"] / totals

    plt.figure(figsize=(8.5, 5.5))
    plt.scatter(
        plot_df["gdp_gap_usd_wb"],
        plot_df["flow_share_sender"],
        s=np.clip(plot_df["flow_count"] / 12, 8, 240),
        alpha=0.45,
        color="#5d6f9f",
        edgecolors="white",
        linewidths=0.3,
    )
    plt.axvline(0, color="#333333", linewidth=1)
    plt.yscale("log")
    plt.xlabel("Receiver GDP pc - sender GDP pc, current US$ (World Bank)")
    plt.ylabel("Flow share within sending country, log scale")
    plt.title("Economic Gap and Destination Flow Share")
    return img_tag(fig_to_base64(), "Scatter plot of GDP per capita gap and Erasmus flow share")


def heatmap_chart(flows: pd.DataFrame) -> str:
    top_senders = flows.groupby("sending_code")["flow_count"].sum().nlargest(14).index
    top_receivers = flows.groupby("receiving_code")["flow_count"].sum().nlargest(14).index
    matrix = flows.loc[flows["sending_code"].isin(top_senders) & flows["receiving_code"].isin(top_receivers)]
    matrix = matrix.pivot_table(
        index="sending_code",
        columns="receiving_code",
        values="flow_count",
        aggfunc="sum",
        fill_value=0,
    )
    matrix = matrix.reindex(index=top_senders, columns=top_receivers)

    plt.figure(figsize=(9, 6.5))
    sns.heatmap(matrix, cmap="YlGnBu", linewidths=0.3, linecolor="white")
    plt.xlabel("Receiving country")
    plt.ylabel("Sending country")
    plt.title("Top Sending and Receiving Country Flows")
    return img_tag(fig_to_base64(), "Heatmap of top Erasmus sending and receiving country flows")


def weighted_destination_table(flows: pd.DataFrame) -> str:
    def weighted_average(group: pd.DataFrame, column: str) -> float:
        valid = group.dropna(subset=[column])
        if valid.empty:
            return np.nan
        return np.average(valid[column], weights=valid["flow_count"])

    rows = []
    for (code, country), group in flows.groupby(["sending_code", "sending_country"]):
        rows.append(
            {
                "Sender": f"{code} - {country}",
                "Outgoing participants": int(group["flow_count"].sum()),
                "Weighted destination GDP pc, US$": weighted_average(group, "receiver_gdp_pc_current_usd_wb"),
                "Weighted destination price level": weighted_average(group, "receiver_price_level_aic_eu27_2020_100"),
                "Weighted destination net earnings, EUR": weighted_average(group, "receiver_net_earnings_eur"),
            }
        )

    table = pd.DataFrame(rows).sort_values("Outgoing participants", ascending=False).head(20)
    for column in table.columns[2:]:
        table[column] = table[column].round(1)
    return table.to_html(index=False, classes="data-table", border=0)


def diagnostics_table(flows: pd.DataFrame) -> str:
    rows = [
        {"Metric": "Cross-border country pairs", "Value": f"{len(flows):,}"},
        {"Metric": "Participants", "Value": f"{flows['flow_count'].sum():,}"},
        {"Metric": "Sending countries", "Value": f"{flows['sending_code'].nunique():,}"},
        {"Metric": "Receiving countries", "Value": f"{flows['receiving_code'].nunique():,}"},
        {
            "Metric": "Rows with World Bank GDP gap",
            "Value": f"{flows['gdp_gap_usd_wb'].notna().sum():,} / {len(flows):,}",
        },
        {
            "Metric": "Rows with Eurostat price gap",
            "Value": f"{flows['price_level_gap'].notna().sum():,} / {len(flows):,}",
        },
    ]
    return pd.DataFrame(rows).to_html(index=False, classes="data-table", border=0)


def build_dashboard() -> str:
    flows = pd.read_csv(DATA_PATH)
    top_destinations = top_destinations_chart(flows)
    italy_luxembourg = italy_luxembourg_chart(flows)
    scatter = scatter_chart(flows)
    heatmap = heatmap_chart(flows)
    weighted_table = weighted_destination_table(flows)
    diagnostics = diagnostics_table(flows)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>unilife.ellep.it</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1f2933;
      --muted: #5f6b76;
      --line: #d8dee4;
      --paper: #f7f7f4;
      --panel: #ffffff;
      --accent: #2f6f73;
    }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--paper);
      color: var(--ink);
    }}
    header {{
      padding: 32px 42px 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 16px;
      font-size: 20px;
      letter-spacing: 0;
    }}
    p {{
      color: var(--muted);
      line-height: 1.5;
      max-width: 920px;
    }}
    main {{
      padding: 28px 42px 48px;
      display: grid;
      gap: 24px;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
      gap: 24px;
    }}
    img {{
      width: 100%;
      height: auto;
      display: block;
    }}
    .data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    .data-table th, .data-table td {{
      border-bottom: 1px solid var(--line);
      padding: 9px 8px;
      text-align: right;
    }}
    .data-table th:first-child, .data-table td:first-child {{
      text-align: left;
    }}
    .note {{
      font-size: 13px;
      color: var(--muted);
    }}
    @media (max-width: 700px) {{
      header, main {{
        padding-left: 18px;
        padding-right: 18px;
      }}
      .grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>unilife.ellep.it</h1>
    <p>Higher Education study mobility flows from the Erasmus+ KA1 2022 researcher file, joined to economic indicators for descriptive analysis. This dashboard is exploratory and does not claim causal effects.</p>
  </header>
  <main>
    <section>
      <h2>Dataset Status</h2>
      {diagnostics}
      <p class="note">Main flow definition: Higher Education learners, study mobility activity, age 18+, cross-border flows only.</p>
    </section>
    <div class="grid">
      <section>
        <h2>Top Destinations</h2>
        {top_destinations}
      </section>
      <section>
        <h2>Italy vs Luxembourg</h2>
        {italy_luxembourg}
      </section>
    </div>
    <div class="grid">
      <section>
        <h2>GDP Gap and Flow Share</h2>
        {scatter}
      </section>
      <section>
        <h2>Flow Heatmap</h2>
        {heatmap}
      </section>
    </div>
    <section>
      <h2>Flow-Weighted Destination Economics</h2>
      {weighted_table}
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    html = build_dashboard()
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
