"""Pulizia delle tabelle PNRR principali."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.config import CLEAN_DATA_DIR, CORE_TABLES, FUNDING_COLUMNS, OPENPNRR_SOURCES, PAYMENT_COLUMNS, RAW_DATA_DIR
from scripts.utils import add_project_key, clean_code, coerce_numeric_columns, latest_snapshot, normalize_columns, read_csv, write_csv


def read_raw_table(source_name: str, snapshot: str | None = None) -> pd.DataFrame:
    """Riceve nome fonte e snapshot, restituisce la tabella raw corrispondente."""
    snapshot_name = snapshot or latest_snapshot(RAW_DATA_DIR)
    source = OPENPNRR_SOURCES[source_name]
    return read_csv(RAW_DATA_DIR / snapshot_name / source["raw_filename"])


def clean_projects(df: pd.DataFrame) -> pd.DataFrame:
    """Riceve progetti raw, normalizza colonne e importi, restituisce progetti puliti."""
    output = normalize_columns(df)
    output = add_project_key(output)
    output = coerce_numeric_columns(output, FUNDING_COLUMNS)
    for column in ["codice_misura", "soggetto_attuatore_cf"]:
        if column in output.columns:
            output[column] = output[column].map(clean_code).astype("string")
    return output


def clean_payments(df: pd.DataFrame) -> pd.DataFrame:
    """Riceve pagamenti raw, normalizza importi e data aggiornamento, restituisce pagamenti puliti."""
    output = normalize_columns(df)
    output = add_project_key(output)
    output = coerce_numeric_columns(output, PAYMENT_COLUMNS)
    if "data_aggiornamento" in output.columns:
        output["data_aggiornamento"] = pd.to_datetime(output["data_aggiornamento"], errors="coerce", dayfirst=True).dt.date.astype("string")
    return output


def clean_locations(df: pd.DataFrame) -> pd.DataFrame:
    """Riceve localizzazioni raw, normalizza identificativi territoriali e restituisce dati puliti."""
    output = normalize_columns(df)
    output = add_project_key(output)
    for column in ["territorio_id", "istat_id", "tipologia"]:
        if column in output.columns:
            output[column] = output[column].map(clean_code).astype("string")
    if "denominazione" in output.columns:
        output["denominazione"] = output["denominazione"].astype("string").str.strip()
    return output


def clean_territories(df: pd.DataFrame) -> pd.DataFrame:
    """Riceve anagrafica territori raw e restituisce identificativi normalizzati."""
    output = normalize_columns(df)
    for column in ["territorio_id", "istat_id", "tipologia"]:
        if column in output.columns:
            output[column] = output[column].map(clean_code).astype("string")
    return output


def build_clean_pnrr_tables(snapshot: str | None = None) -> Path:
    """Riceve uno snapshot raw, salva le tabelle pulite e restituisce la cartella clean."""
    snapshot_name = snapshot or latest_snapshot(RAW_DATA_DIR)
    output_dir = CLEAN_DATA_DIR / snapshot_name
    output_dir.mkdir(parents=True, exist_ok=True)
    cleaners = {"projects": clean_projects, "payments": clean_payments, "locations": clean_locations, "territories": clean_territories}
    for table_name in CORE_TABLES:
        raw = read_raw_table(table_name, snapshot=snapshot_name)
        clean = cleaners[table_name](raw)
        write_csv(clean, output_dir / OPENPNRR_SOURCES[table_name]["clean_filename"])
    return output_dir


def main() -> None:
    """Esegue la pulizia sullo snapshot raw più recente e non restituisce valori."""
    output_dir = build_clean_pnrr_tables()
    print(f"Dati puliti salvati in: {output_dir}")


if __name__ == "__main__":
    main()
