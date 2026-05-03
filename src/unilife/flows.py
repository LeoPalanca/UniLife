from pathlib import Path

import pandas as pd


RAW_ANNEX = Path("data/raw/annual-report-2024-statistical-annex.xlsx")
DEFAULT_SHEET = "HE-Learn Mobility"


def load_flow_matrix(path: str | Path = RAW_ANNEX, sheet_name: str = DEFAULT_SHEET) -> pd.DataFrame:
    """Load the Erasmus sending x receiving country matrix from the statistical annex."""
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    receiving_codes = raw.iloc[4, 5:38].dropna().tolist()
    rows = raw.iloc[6:, [2, 3, 4] + list(range(5, 5 + len(receiving_codes)))].dropna(subset=[2, 3])
    rows.columns = ["sending_country", "sending_code", "grand_total", *receiving_codes]
    return rows


def reshape_flows_long(matrix: pd.DataFrame, include_domestic: bool = False) -> pd.DataFrame:
    """Convert the country-pair flow matrix to long format."""
    id_vars = ["sending_country", "sending_code", "grand_total"]
    receiving_codes = [column for column in matrix.columns if column not in id_vars]

    flows = matrix.melt(
        id_vars=id_vars,
        value_vars=receiving_codes,
        var_name="receiving_code",
        value_name="flow_count",
    )
    flows["flow_count"] = pd.to_numeric(flows["flow_count"], errors="coerce").fillna(0).astype(int)

    if not include_domestic:
        flows = flows.loc[flows["sending_code"] != flows["receiving_code"]]

    return flows.reset_index(drop=True)
