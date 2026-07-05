"""Pulizia delle tabelle PNRR principali."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.config import CLEAN_DATA_DIR, CORE_TABLES, FUNDING_COLUMNS, OPENPNRR_SOURCES, PAYMENT_COLUMNS, RAW_DATA_DIR, SAVE_CLEAN_JSON
from scripts.utils import add_project_key, clean_code, coerce_numeric_columns, latest_snapshot, normalize_columns, read_csv, write_table_outputs


def read_raw_table(source_name: str, snapshot: str | None = None) -> pd.DataFrame:
    """Riceve nome fonte e snapshot, restituisce la tabella raw corrispondente."""
    snapshot_name = snapshot or latest_snapshot(RAW_DATA_DIR)
    source = OPENPNRR_SOURCES[source_name]
    return read_csv(RAW_DATA_DIR / snapshot_name / source["raw_filename"])


def clean_projects(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizza progetti, chiave progetto e importi di finanziamento."""
    output = normalize_columns(df)
    output = add_project_key(output)
    output = coerce_numeric_columns(output, FUNDING_COLUMNS)
    for column in ["cup", "codice_locale_progetto", "codice_misura", "soggetto_attuatore_cf"]:
        if column in output.columns:
            output[column] = output[column].map(clean_code).astype("string")
    return output.drop_duplicates().reset_index(drop=True)


def clean_payments(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizza pagamenti, chiave progetto, importi e data aggiornamento."""
    output = normalize_columns(df)
    output = add_project_key(output)
    output = coerce_numeric_columns(output, PAYMENT_COLUMNS)
    if "data_aggiornamento" in output.columns:
        output["data_aggiornamento"] = pd.to_datetime(output["data_aggiornamento"], errors="coerce", dayfirst=True).dt.date.astype("string")
    return output.drop_duplicates().reset_index(drop=True)


def clean_locations(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizza localizzazioni progetto-territorio.

    La tabella può contenere solo `progetto_id` e `territorio_id`. La chiave
    `project_key` viene costruita con la stessa regola usata per progetti e
    pagamenti, così il join resta stabile anche con colonne diverse.
    """
    output = normalize_columns(df)
    output = add_project_key(output)
    if "id" in output.columns and "territorio_id" not in output.columns:
        output = output.rename(columns={"id": "territorio_id"})
    for column in ["territorio_id", "istat_id", "tipologia"]:
        if column in output.columns:
            output[column] = output[column].map(clean_code).astype("string")
    if "denominazione" in output.columns:
        output["denominazione"] = output["denominazione"].astype("string").str.strip()
    keep = [column for column in ["project_key", "territorio_id", "istat_id", "tipologia", "denominazione"] if column in output.columns]
    return output[keep].drop_duplicates().reset_index(drop=True)


def clean_territories(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizza l'anagrafica territoriale e rende stabile `territorio_id`."""
    output = normalize_columns(df)
    if "id" in output.columns and "territorio_id" not in output.columns:
        output = output.rename(columns={"id": "territorio_id"})
    for column in ["territorio_id", "parent_id", "istat_id", "tipologia", "identifier"]:
        if column in output.columns:
            output[column] = output[column].map(clean_code).astype("string")
    if "denominazione" in output.columns:
        output["denominazione"] = output["denominazione"].astype("string").str.strip()
    keep = [column for column in ["territorio_id", "parent_id", "istat_id", "tipologia", "identifier", "denominazione"] if column in output.columns]
    return output[keep].drop_duplicates().reset_index(drop=True)


def build_clean_pnrr_tables(snapshot: str | None = None) -> Path:
    """Salva le tabelle pulite in CSV e JSON e restituisce la cartella clean."""
    snapshot_name = snapshot or latest_snapshot(RAW_DATA_DIR)
    output_dir = CLEAN_DATA_DIR / snapshot_name
    output_dir.mkdir(parents=True, exist_ok=True)
    cleaners = {"projects": clean_projects, "payments": clean_payments, "locations": clean_locations, "territories": clean_territories}
    report = []
    for table_name in CORE_TABLES:
        raw = read_raw_table(table_name, snapshot=snapshot_name)
        clean = cleaners[table_name](raw)
        output_path = output_dir / OPENPNRR_SOURCES[table_name]["clean_filename"]
        write_table_outputs(clean, output_path, save_json_output=SAVE_CLEAN_JSON)
        report.append({"table": table_name, "raw_rows": len(raw), "clean_rows": len(clean), "columns": clean.shape[1], "path": str(output_path)})
    write_table_outputs(pd.DataFrame(report), output_dir / "cleaning_report.csv", save_json_output=SAVE_CLEAN_JSON)
    return output_dir


def main() -> None:
    """Esegue la pulizia sullo snapshot raw più recente."""
    output_dir = build_clean_pnrr_tables()
    print(f"Dati puliti salvati in: {output_dir}")


if __name__ == "__main__":
    main()
