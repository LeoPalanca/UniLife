from __future__ import annotations

from itertools import product

import pandas as pd
import requests


EUROSTAT_API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"


def jsonstat_to_frame(data: dict) -> pd.DataFrame:
    """Convert a compact JSON-stat response from Eurostat to a tidy dataframe."""
    ids = data["id"]
    sizes = data["size"]
    categories: list[list[str]] = []
    labels: dict[str, dict[str, str]] = {}

    for dim in ids:
        category = data["dimension"][dim]["category"]
        index = category["index"]
        ordered = sorted(index, key=index.get)
        categories.append(ordered)
        labels[dim] = category.get("label", {})

    rows = []
    for flat_index, codes in enumerate(product(*categories)):
        value = data.get("value", {}).get(str(flat_index))
        if value is None:
            continue
        row = {"value": value}
        for dim, code in zip(ids, codes):
            row[dim] = code
            row[f"{dim}_label"] = labels[dim].get(code, code)
        rows.append(row)

    return pd.DataFrame(rows)


def fetch_eurostat(dataset: str, **filters: str) -> pd.DataFrame:
    """Fetch a filtered Eurostat dataset through the statistics API."""
    params = {"format": "JSON", "lang": "en", **filters}
    response = requests.get(f"{EUROSTAT_API}/{dataset}", params=params, timeout=60)
    response.raise_for_status()
    return jsonstat_to_frame(response.json())


def fetch_country_indicators(year: int = 2022) -> pd.DataFrame:
    """Fetch the country-level indicators used in the descriptive flow analysis."""
    gdp = fetch_eurostat("nama_10_pc", time=str(year), unit="CP_EUR_HAB", na_item="B1GQ")
    gdp = gdp[["geo", "geo_label", "value"]].rename(
        columns={"geo": "country_code", "geo_label": "country_name", "value": "gdp_pc_eur"}
    )

    prices = fetch_eurostat("prc_ppp_ind", time=str(year), na_item="PLI_EU27_2020", ppp_cat="A01")
    prices = prices[["geo", "geo_label", "value"]].rename(
        columns={
            "geo": "country_code",
            "geo_label": "price_country_name",
            "value": "price_level_aic_eu27_2020_100",
        }
    )

    earnings = fetch_eurostat(
        "earn_nt_net",
        time=str(year),
        currency="EUR",
        estruct="NET",
        ecase="P1_NCH_AW100",
    )
    earnings = earnings[["geo", "geo_label", "value"]].rename(
        columns={"geo": "country_code", "geo_label": "earnings_country_name", "value": "net_earnings_eur"}
    )

    world_bank = fetch_world_bank_gdp_per_capita(year=year)

    indicators = (
        gdp.merge(prices, on="country_code", how="outer")
        .merge(earnings, on="country_code", how="outer")
        .merge(world_bank, on="country_code", how="outer")
    )
    indicators["country_name"] = indicators["country_name"].fillna(indicators.pop("price_country_name"))
    indicators["country_name"] = indicators["country_name"].fillna(indicators.pop("earnings_country_name"))
    indicators["country_name"] = indicators["country_name"].fillna(indicators["wb_country_name"])
    indicators["year"] = year
    return indicators.sort_values("country_code").reset_index(drop=True)


def fetch_sector_earnings(year: int | None = None) -> pd.DataFrame:
    """Fetch EU mean monthly gross earnings by country and economic sector (NACE).

    Discover the latest SES year in the consolidated table, then use that wave's
    detailed NACE table. Employers with 10+ employees; all sexes and lengths of service.
    """
    if year is None:
        releases = fetch_eurostat("earn_ses_monthly", indic_se="MEAN_E_EUR", sex="T",
                                  age="TOTAL", isco08="TOTAL", worktime="TOTAL",
                                  nace_r2="B-S_X_O", freq="A")
        if releases.empty:
            raise ValueError("No published monthly SES observations")
        year = int(pd.to_numeric(releases["time"]).max())
    frames = []
    for unit, column in (("EUR", "earnings_eur"), ("PPS", "earnings_pps")):
        data = fetch_eurostat(
            f"earn_ses{year % 100:02d}_24",
            time=str(year), indic_se="ERN", unit=unit,
            sex="T",
            sizeclas="GE10", l_serv="TOTAL",
            freq="A",
        )
        if data.empty:
            raise ValueError(f"No detailed monthly sector earnings for {unit}, year {year}")
        data = data[["geo", "geo_label", "nace_r2", "nace_r2_label", "value"]].rename(
            columns={
                "geo": "country_code",
                "geo_label": "country_name",
                "nace_r2": "nace_code",
                "nace_r2_label": "nace_label",
                "value": column,
            }
        )
        frames.append(data)

    merged = frames[0].merge(
        frames[1][["country_code", "nace_code", "country_name", "nace_label", "earnings_pps"]],
        on=["country_code", "nace_code"],
        how="outer", suffixes=("", "_pps"), validate="one_to_one",
    )
    for label in ("country_name", "nace_label"):
        merged[label] = merged[label].fillna(merged.pop(f"{label}_pps"))
    merged = merged[~merged["country_code"].str.startswith(("EU", "EA"))]
    # NACE single-letter codes are the detailed sectors; multi-character codes are aggregates.
    merged["is_sector"] = merged["nace_code"].str.fullmatch(r"[A-Z]")
    if not merged["is_sector"].any():
        raise ValueError("SES response has no detailed NACE sectors")
    merged["country_code"] = merged["country_code"].replace({"GB": "UK", "GR": "EL"})
    merged["year"] = year
    return merged.sort_values(["country_code", "nace_code"]).reset_index(drop=True)


def fetch_world_bank_gdp_per_capita(year: int = 2022) -> pd.DataFrame:
    """Fetch broad-country-coverage GDP per capita from the World Bank."""
    response = requests.get(
        "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD",
        params={"format": "json", "date": str(year), "per_page": "20000"},
        timeout=60,
    )
    response.raise_for_status()
    rows = response.json()[1]
    frame = pd.DataFrame(
        {
            "country_code": row["country"]["id"],
            "wb_country_name": row["country"]["value"],
            "gdp_pc_current_usd_wb": row["value"],
        }
        for row in rows
        if row.get("value") is not None
    )
    frame["country_code"] = frame["country_code"].replace({"GB": "UK", "GR": "EL"})
    return frame


def join_indicators(flows: pd.DataFrame, indicators: pd.DataFrame) -> pd.DataFrame:
    """Join sender and receiver country indicators to a country-pair flow table."""
    sender = indicators.add_prefix("sender_").rename(columns={"sender_country_code": "sending_code"})
    receiver = indicators.add_prefix("receiver_").rename(columns={"receiver_country_code": "receiving_code"})

    joined = flows.merge(sender, on="sending_code", how="left").merge(receiver, on="receiving_code", how="left")
    joined["gdp_gap"] = joined["receiver_gdp_pc_eur"] - joined["sender_gdp_pc_eur"]
    joined["gdp_gap_usd_wb"] = joined["receiver_gdp_pc_current_usd_wb"] - joined["sender_gdp_pc_current_usd_wb"]
    joined["price_level_gap"] = (
        joined["receiver_price_level_aic_eu27_2020_100"] - joined["sender_price_level_aic_eu27_2020_100"]
    )
    joined["earnings_gap"] = joined["receiver_net_earnings_eur"] - joined["sender_net_earnings_eur"]
    return joined


def indicator_coverage(joined: pd.DataFrame) -> pd.DataFrame:
    """Summarize indicator missingness after joining economic data to flows."""
    checks = [
        ("sender_gdp_pc_eur", "sender GDP per capita"),
        ("receiver_gdp_pc_eur", "receiver GDP per capita"),
        ("sender_gdp_pc_current_usd_wb", "sender GDP per capita World Bank"),
        ("receiver_gdp_pc_current_usd_wb", "receiver GDP per capita World Bank"),
        ("sender_price_level_aic_eu27_2020_100", "sender price level"),
        ("receiver_price_level_aic_eu27_2020_100", "receiver price level"),
        ("sender_net_earnings_eur", "sender net earnings"),
        ("receiver_net_earnings_eur", "receiver net earnings"),
    ]
    rows = []
    for column, label in checks:
        missing = joined[column].isna()
        rows.append(
            {
                "indicator": label,
                "missing_rows": int(missing.sum()),
                "missing_flow_count": int(joined.loc[missing, "flow_count"].sum()),
            }
        )
    return pd.DataFrame(rows)
