"""Costruzione degli indicatori PNRR finanziari e territoriali."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.config import CLEAN_DATA_DIR, FUNDING_COLUMNS, INDICATORS_DATA_DIR, PAYMENT_COLUMNS, TERRITORY_OUTPUT_FILES, TERRITORY_PRIORITY
from scripts.utils import latest_snapshot, read_csv, safe_divide, write_csv, write_json_records


def load_clean_tables(snapshot: str | None = None) -> dict[str, pd.DataFrame]:
    """Riceve uno snapshot clean e restituisce progetti, pagamenti, localizzazioni e territori."""
    snapshot_name = snapshot or latest_snapshot(CLEAN_DATA_DIR)
    snapshot_dir = CLEAN_DATA_DIR / snapshot_name
    return {
        "projects": read_csv(snapshot_dir / "projects.csv"),
        "payments": read_csv(snapshot_dir / "payments.csv"),
        "locations": read_csv(snapshot_dir / "locations.csv"),
        "territories": read_csv(snapshot_dir / "territories.csv"),
    }


def save_indicator(df: pd.DataFrame, path: Path) -> None:
    """Salva un indicatore in CSV e JSON."""
    write_csv(df, path)
    write_json_records(df, path.with_suffix(".json"))


def add_financial_ratios(df: pd.DataFrame, suffix: str = "") -> pd.DataFrame:
    """Aggiunge rapporti pagamento/finanziamento a una tabella con importi.

    Args:
        df: tabella con colonne di pagamento e finanziamento.
        suffix: suffisso usato per colonne allocate.

    Returns:
        Copia della tabella con rapporti finanziari.
    """
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
    """Unisce progetti e pagamenti su `project_key` e restituisce progetti arricchiti.

    I pagamenti sono aggregati per progetto perché la fonte può contenere più
    righe per lo stesso progetto e diverse fonti di pagamento.
    """
    value_columns = [column for column in PAYMENT_COLUMNS if column in payments.columns]
    aggregations = {column: "sum" for column in value_columns}
    if "data_aggiornamento" in payments.columns:
        aggregations["data_aggiornamento"] = "max"
    reduced_payments = payments.groupby("project_key", dropna=False, as_index=False).agg(aggregations) if aggregations else payments[["project_key"]].drop_duplicates()
    output = projects.merge(reduced_payments, on="project_key", how="left")
    for column in PAYMENT_COLUMNS:
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce").fillna(0.0)
    return add_financial_ratios(output)


def attach_territory_registry(locations: pd.DataFrame, territories: pd.DataFrame) -> pd.DataFrame:
    """Aggiunge denominazione, tipologia e codici territoriali alle localizzazioni."""
    territory_columns = [column for column in ["territorio_id", "istat_id", "tipologia", "denominazione", "parent_id"] if column in territories.columns]
    enriched = locations.merge(territories[territory_columns], on="territorio_id", how="left", suffixes=("", "_registry"))
    for column in ["istat_id", "tipologia", "denominazione"]:
        registry_column = f"{column}_registry"
        if registry_column in enriched.columns:
            if column in enriched.columns:
                enriched[column] = enriched[column].fillna(enriched[registry_column])
            else:
                enriched[column] = enriched[registry_column]
            enriched = enriched.drop(columns=[registry_column])
    return enriched


def expand_projects_by_territory(projects_payments: pd.DataFrame, locations: pd.DataFrame, territories: pd.DataFrame) -> pd.DataFrame:
    """Restituisce righe progetto-territorio al livello più fine disponibile.

    Criterio metodologico: per ogni progetto si seleziona la localizzazione con
    priorità territoriale più alta. L'ordine è comune, città metropolitana,
    provincia, regione. Questo evita che lo stesso progetto entri con importo
    pieno in più livelli quando la fonte contiene localizzazioni ridondanti.
    """
    enriched_locations = attach_territory_registry(locations, territories)
    required = ["project_key", "territorio_id", "istat_id", "denominazione", "tipologia"]
    available = [column for column in required if column in enriched_locations.columns]
    territory_projects = enriched_locations[available].merge(projects_payments, on="project_key", how="left")
    territory_projects["territory_priority"] = territory_projects["tipologia"].map(TERRITORY_PRIORITY).fillna(0).astype(int)
    territory_projects["max_territory_priority"] = territory_projects.groupby("project_key")["territory_priority"].transform("max")
    territory_projects = territory_projects.loc[territory_projects["territory_priority"] == territory_projects["max_territory_priority"]].copy()
    territory_projects = territory_projects.loc[territory_projects["territory_priority"] > 0].copy()
    return territory_projects


def apply_equal_territorial_allocation(territory_projects: pd.DataFrame) -> pd.DataFrame:
    """Ripartisce uniformemente importi e pagamenti tra localizzazioni selezionate.

    Se un progetto ha due comuni selezionati, ogni comune riceve metà degli
    importi. La regola è documentata perché la fonte non pubblica quote
    territoriali specifiche per progetto.
    """
    output = territory_projects.copy()
    output["n_selected_locations"] = output.groupby("project_key")["territorio_id"].transform("nunique").replace(0, pd.NA)
    output["allocation_weight_equal"] = 1 / output["n_selected_locations"]
    for column in [*FUNDING_COLUMNS, *PAYMENT_COLUMNS]:
        if column in output.columns:
            output[f"{column}_allocated"] = pd.to_numeric(output[column], errors="coerce").fillna(0.0) * output["allocation_weight_equal"]
    return output


def aggregate_national(projects_payments: pd.DataFrame) -> pd.DataFrame:
    """Restituisce una sintesi nazionale senza duplicazioni territoriali."""
    value_columns = [column for column in [*FUNDING_COLUMNS, *PAYMENT_COLUMNS] if column in projects_payments]
    summary = projects_payments[value_columns].sum(numeric_only=True).to_frame().T
    summary.insert(0, "projects_count", projects_payments["project_key"].nunique())
    summary.insert(0, "territory_level", "N")
    summary.insert(0, "territory_name", "Italia")
    summary.insert(0, "territory_id", "IT")
    return add_financial_ratios(summary)


def aggregate_territory_level(territory_projects: pd.DataFrame, territory_level: str) -> pd.DataFrame:
    """Aggrega importi allocati per livello territoriale."""
    subset = territory_projects.loc[territory_projects["tipologia"] == territory_level].copy()
    if subset.empty:
        return pd.DataFrame(columns=["territory_id", "territory_name", "territory_level", "projects_count"])
    group_columns = ["istat_id", "denominazione", "tipologia"]
    value_columns = [column for column in subset.columns if column.endswith("_allocated")]
    aggregated = subset.groupby(group_columns, dropna=False)[value_columns].sum().reset_index()
    counts = subset.groupby(group_columns, dropna=False)["project_key"].nunique().reset_index().rename(columns={"project_key": "projects_count"})
    weights = subset.groupby(group_columns, dropna=False)["allocation_weight_equal"].sum().reset_index().rename(columns={"allocation_weight_equal": "weighted_projects_count"})
    aggregated = aggregated.merge(counts, on=group_columns, how="left").merge(weights, on=group_columns, how="left")
    aggregated = aggregated.rename(columns={"istat_id": "territory_id", "denominazione": "territory_name", "tipologia": "territory_level"})
    return add_financial_ratios(aggregated, suffix="_allocated").sort_values("territory_name", na_position="last")


def build_pnrr_indicators(snapshot: str | None = None) -> Path:
    """Salva indicatori nazionali e territoriali e restituisce la cartella output."""
    snapshot_name = snapshot or latest_snapshot(CLEAN_DATA_DIR)
    output_dir = INDICATORS_DATA_DIR / snapshot_name
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = load_clean_tables(snapshot_name)
    projects_payments = merge_projects_with_payments(tables["projects"], tables["payments"])
    territory_projects = apply_equal_territorial_allocation(expand_projects_by_territory(projects_payments, tables["locations"], tables["territories"]))
    save_indicator(projects_payments, output_dir / "projects_payments.csv")
    save_indicator(territory_projects, output_dir / "territory_projects.csv")
    save_indicator(aggregate_national(projects_payments), output_dir / "national_summary.csv")
    summaries = {}
    for level, filename in TERRITORY_OUTPUT_FILES.items():
        summary = aggregate_territory_level(territory_projects, level)
        summaries[level] = summary
        save_indicator(summary, output_dir / filename)
    province_like = [summaries.get("P", pd.DataFrame()), summaries.get("CM", pd.DataFrame())]
    province_like = [df for df in province_like if not df.empty]
    if province_like:
        save_indicator(pd.concat(province_like, ignore_index=True), output_dir / "province_and_metropolitan_city_summary.csv")
    return output_dir


def main() -> None:
    """Costruisce gli indicatori sullo snapshot clean più recente."""
    output_dir = build_pnrr_indicators()
    print(f"Indicatori salvati in: {output_dir}")


if __name__ == "__main__":
    main()
