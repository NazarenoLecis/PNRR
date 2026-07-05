"""Costruzione degli indicatori PNRR finanziari e territoriali."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.config import CLEAN_DATA_DIR, FUNDING_COLUMNS, INDICATORS_DATA_DIR, PAYMENT_COLUMNS, TERRITORY_OUTPUT_FILES
from scripts.utils import latest_snapshot, read_csv, safe_divide, write_csv


def load_clean_tables(snapshot: str | None = None) -> dict[str, pd.DataFrame]:
    """Riceve uno snapshot clean e restituisce dizionario con progetti, pagamenti, localizzazioni e territori."""
    snapshot_name = snapshot or latest_snapshot(CLEAN_DATA_DIR)
    snapshot_dir = CLEAN_DATA_DIR / snapshot_name
    return {"projects": read_csv(snapshot_dir / "projects.csv"), "payments": read_csv(snapshot_dir / "payments.csv"), "locations": read_csv(snapshot_dir / "locations.csv"), "territories": read_csv(snapshot_dir / "territories.csv")}


def add_financial_ratios(df: pd.DataFrame, suffix: str = "") -> pd.DataFrame:
    """Riceve una tabella con importi, aggiunge rapporti pagamento/finanziamento e restituisce una copia."""
    output = df.copy()
    pnrr_payment = f"pagamento_pnrr{suffix}"
    pnrr_funding = f"finanziamento_pnrr{suffix}"
    total_payment = f"pagamento_tot{suffix}"
    total_funding = f"finanziamento_totale{suffix}"
    if {pnrr_payment, pnrr_funding}.issubset(output.columns):
        output[f"payment_progress_pnrr{suffix}"] = safe_divide(output[pnrr_payment], output[pnrr_funding])
    if {total_payment, total_funding}.issubset(output.columns):
        output[f"payment_progress_total{suffix}"] = safe_divide(output[total_payment], output[total_funding])
    return output


def merge_projects_with_payments(projects: pd.DataFrame, payments: pd.DataFrame) -> pd.DataFrame:
    """Riceve progetti e pagamenti, esegue il join su project_key e restituisce progetti arricchiti."""
    payment_columns = ["project_key"] + [column for column in PAYMENT_COLUMNS if column in payments.columns]
    if "data_aggiornamento" in payments.columns:
        payment_columns.append("data_aggiornamento")
    reduced_payments = payments[payment_columns].drop_duplicates("project_key")
    output = projects.merge(reduced_payments, on="project_key", how="left")
    for column in PAYMENT_COLUMNS:
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce").fillna(0.0)
    return add_financial_ratios(output)


def expand_projects_by_territory(projects_payments: pd.DataFrame, locations: pd.DataFrame) -> pd.DataFrame:
    """Riceve progetti con pagamenti e localizzazioni, restituisce righe progetto-territorio."""
    location_columns = [column for column in ["project_key", "territorio_id", "istat_id", "denominazione", "tipologia"] if column in locations.columns]
    return locations[location_columns].merge(projects_payments, on="project_key", how="left")


def apply_equal_territorial_allocation(territory_projects: pd.DataFrame) -> pd.DataFrame:
    """Riceve righe progetto-territorio e restituisce importi ripartiti uniformemente per livello."""
    output = territory_projects.copy()
    output["n_locations_same_level"] = output.groupby(["project_key", "tipologia"])["territorio_id"].transform("nunique").replace(0, pd.NA)
    output["allocation_weight_equal"] = 1 / output["n_locations_same_level"]
    for column in [*FUNDING_COLUMNS, *PAYMENT_COLUMNS]:
        if column in output.columns:
            output[f"{column}_allocated"] = pd.to_numeric(output[column], errors="coerce").fillna(0.0) * output["allocation_weight_equal"]
    return output


def aggregate_national(projects_payments: pd.DataFrame) -> pd.DataFrame:
    """Riceve progetti con pagamenti e restituisce una sintesi nazionale senza duplicazioni territoriali."""
    value_columns = [column for column in [*FUNDING_COLUMNS, *PAYMENT_COLUMNS] if column in projects_payments]
    summary = projects_payments[value_columns].sum(numeric_only=True).to_frame().T
    summary.insert(0, "projects_count", projects_payments["project_key"].nunique())
    summary.insert(0, "territory_level", "N")
    summary.insert(0, "territory_name", "Italia")
    summary.insert(0, "territory_id", "IT")
    return add_financial_ratios(summary)


def aggregate_territory_level(territory_projects: pd.DataFrame, territory_level: str) -> pd.DataFrame:
    """Riceve righe progetto-territorio e un livello, restituisce aggregati territoriali allocati."""
    subset = territory_projects.loc[territory_projects["tipologia"] == territory_level].copy()
    if subset.empty:
        return pd.DataFrame()
    group_columns = ["istat_id", "denominazione", "tipologia"]
    value_columns = [column for column in subset.columns if column.endswith("_allocated")]
    aggregated = subset.groupby(group_columns, dropna=False)[value_columns].sum().reset_index()
    counts = subset.groupby(group_columns, dropna=False)["project_key"].nunique().reset_index().rename(columns={"project_key": "projects_count"})
    aggregated = aggregated.merge(counts, on=group_columns, how="left")
    aggregated = aggregated.rename(columns={"istat_id": "territory_id", "denominazione": "territory_name", "tipologia": "territory_level"})
    return add_financial_ratios(aggregated, suffix="_allocated").sort_values("territory_name", na_position="last")


def build_pnrr_indicators(snapshot: str | None = None) -> Path:
    """Riceve uno snapshot clean, salva indicatori territoriali e restituisce la cartella indicatori."""
    snapshot_name = snapshot or latest_snapshot(CLEAN_DATA_DIR)
    output_dir = INDICATORS_DATA_DIR / snapshot_name
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = load_clean_tables(snapshot_name)
    projects_payments = merge_projects_with_payments(tables["projects"], tables["payments"])
    territory_projects = apply_equal_territorial_allocation(expand_projects_by_territory(projects_payments, tables["locations"]))
    write_csv(projects_payments, output_dir / "projects_payments.csv")
    write_csv(territory_projects, output_dir / "territory_projects.csv")
    write_csv(aggregate_national(projects_payments), output_dir / "national_summary.csv")
    summaries = {}
    for level, filename in TERRITORY_OUTPUT_FILES.items():
        summary = aggregate_territory_level(territory_projects, level)
        summaries[level] = summary
        write_csv(summary, output_dir / filename)
    province_like = [summaries.get("P", pd.DataFrame()), summaries.get("CM", pd.DataFrame())]
    province_like = [df for df in province_like if not df.empty]
    if province_like:
        write_csv(pd.concat(province_like, ignore_index=True), output_dir / "province_and_metropolitan_city_summary.csv")
    return output_dir


def main() -> None:
    """Costruisce gli indicatori sullo snapshot clean più recente e non restituisce valori."""
    output_dir = build_pnrr_indicators()
    print(f"Indicatori salvati in: {output_dir}")


if __name__ == "__main__":
    main()
