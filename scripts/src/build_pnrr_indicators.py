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
    """Aggiunge rapporti pagamento/finanziamento a una tabella con importi."""
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
    """Unisce progetti e pagamenti su `project_key` dopo aggregazione per progetto."""
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
    """Aggiunge denominazione, tipologia, parent e codici territoriali alle localizzazioni."""
    territory_columns = [column for column in ["territorio_id", "istat_id", "tipologia", "denominazione", "parent_id"] if column in territories.columns]
    enriched = locations.merge(territories[territory_columns], on="territorio_id", how="left", suffixes=("", "_registry"))
    for column in ["istat_id", "tipologia", "denominazione", "parent_id"]:
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

    Per ogni progetto si seleziona la localizzazione con priorità più alta:
    comune, città metropolitana, provincia, regione. Gli aggregati regionali e
    provinciali sono poi costruiti con roll-up gerarchico sui territori padre.
    """
    enriched_locations = attach_territory_registry(locations, territories)
    required = ["project_key", "territorio_id", "istat_id", "denominazione", "tipologia", "parent_id"]
    available = [column for column in required if column in enriched_locations.columns]
    territory_projects = enriched_locations[available].merge(projects_payments, on="project_key", how="left")
    territory_projects["territory_priority"] = territory_projects["tipologia"].map(TERRITORY_PRIORITY).fillna(0).astype(int)
    territory_projects["max_territory_priority"] = territory_projects.groupby("project_key")["territory_priority"].transform("max")
    territory_projects = territory_projects.loc[territory_projects["territory_priority"] == territory_projects["max_territory_priority"]].copy()
    territory_projects = territory_projects.loc[territory_projects["territory_priority"] > 0].copy()
    return territory_projects


def apply_equal_territorial_allocation(territory_projects: pd.DataFrame) -> pd.DataFrame:
    """Ripartisce uniformemente importi e pagamenti tra localizzazioni selezionate."""
    output = territory_projects.copy()
    output["n_selected_locations"] = output.groupby("project_key")["territorio_id"].transform("nunique").replace(0, pd.NA)
    output["allocation_weight_equal"] = 1 / output["n_selected_locations"]
    for column in [*FUNDING_COLUMNS, *PAYMENT_COLUMNS]:
        if column in output.columns:
            output[f"{column}_allocated"] = pd.to_numeric(output[column], errors="coerce").fillna(0.0) * output["allocation_weight_equal"]
    return output


def territory_lookup(territories: pd.DataFrame) -> dict[str, dict[str, object]]:
    """Restituisce un dizionario territorio_id -> attributi territoriali."""
    columns = [column for column in ["territorio_id", "parent_id", "istat_id", "tipologia", "denominazione"] if column in territories.columns]
    registry = territories[columns].drop_duplicates("territorio_id")
    return registry.set_index("territorio_id").to_dict(orient="index")


def find_ancestor(territory_id: object, lookup: dict[str, dict[str, object]], target_levels: set[str]) -> dict[str, object] | None:
    """Cerca il primo territorio antenato con tipologia compresa in target_levels."""
    current = str(territory_id) if pd.notna(territory_id) else ""
    seen: set[str] = set()
    while current and current not in seen and current in lookup:
        seen.add(current)
        record = lookup[current]
        if record.get("tipologia") in target_levels:
            return {"territory_id": current, **record}
        parent = record.get("parent_id")
        current = str(parent) if pd.notna(parent) else ""
    return None


def add_rollup_columns(territory_projects: pd.DataFrame, territories: pd.DataFrame, target_levels: set[str]) -> pd.DataFrame:
    """Aggiunge colonne di roll-up verso regione, provincia, città metropolitana o comune."""
    lookup = territory_lookup(territories)
    rows = []
    for territory_id in territory_projects["territorio_id"]:
        ancestor = find_ancestor(territory_id, lookup, target_levels)
        rows.append(ancestor or {})
    ancestors = pd.DataFrame(rows, index=territory_projects.index)
    output = territory_projects.copy()
    output["rollup_territory_id"] = ancestors.get("territory_id")
    output["rollup_istat_id"] = ancestors.get("istat_id")
    output["rollup_name"] = ancestors.get("denominazione")
    output["rollup_level"] = ancestors.get("tipologia")
    return output.dropna(subset=["rollup_territory_id"])


def aggregate_rollup_level(territory_projects: pd.DataFrame, territories: pd.DataFrame, target_levels: set[str]) -> pd.DataFrame:
    """Aggrega importi allocati dopo roll-up gerarchico al livello richiesto."""
    rolled = add_rollup_columns(territory_projects, territories, target_levels)
    if rolled.empty:
        return pd.DataFrame(columns=["territory_id", "territory_name", "territory_level", "projects_count"])
    group_columns = ["rollup_istat_id", "rollup_name", "rollup_level"]
    value_columns = [column for column in rolled.columns if column.endswith("_allocated")]
    aggregated = rolled.groupby(group_columns, dropna=False)[value_columns].sum().reset_index()
    counts = rolled.groupby(group_columns, dropna=False)["project_key"].nunique().reset_index().rename(columns={"project_key": "projects_count"})
    weights = rolled.groupby(group_columns, dropna=False)["allocation_weight_equal"].sum().reset_index().rename(columns={"allocation_weight_equal": "weighted_projects_count"})
    aggregated = aggregated.merge(counts, on=group_columns, how="left").merge(weights, on=group_columns, how="left")
    aggregated = aggregated.rename(columns={"rollup_istat_id": "territory_id", "rollup_name": "territory_name", "rollup_level": "territory_level"})
    return add_financial_ratios(aggregated, suffix="_allocated").sort_values("territory_name", na_position="last")


def aggregate_national(projects_payments: pd.DataFrame) -> pd.DataFrame:
    """Restituisce una sintesi nazionale senza duplicazioni territoriali."""
    value_columns = [column for column in [*FUNDING_COLUMNS, *PAYMENT_COLUMNS] if column in projects_payments]
    summary = projects_payments[value_columns].sum(numeric_only=True).to_frame().T
    summary.insert(0, "projects_count", projects_payments["project_key"].nunique())
    summary.insert(0, "territory_level", "N")
    summary.insert(0, "territory_name", "Italia")
    summary.insert(0, "territory_id", "IT")
    return add_financial_ratios(summary)


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

    level_targets = {"R": {"R"}, "P": {"P"}, "CM": {"CM"}, "C": {"C"}}
    summaries = {}
    for level, filename in TERRITORY_OUTPUT_FILES.items():
        summary = aggregate_rollup_level(territory_projects, tables["territories"], level_targets[level])
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
