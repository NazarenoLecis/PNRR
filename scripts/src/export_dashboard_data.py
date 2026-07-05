"""Esportazione leggera dei dati per dashboard statica.

La dashboard non deve leggere raw, clean o indicatori completi. Questo script
crea un solo JSON compatto con tabelle aggregate e colonne essenziali.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.config import DASHBOARD_DATA_DIR, DASHBOARD_SETTINGS, INDICATORS_DATA_DIR, SAVE_DASHBOARD_JSON
from scripts.utils import latest_snapshot, read_csv, save_json, utc_now_iso, write_csv

NATIONAL_COLUMNS = [
    "territory_id",
    "territory_name",
    "territory_level",
    "projects_count",
    "finanziamento_pnrr",
    "pagamento_pnrr",
    "payment_progress_pnrr",
    "finanziamento_totale",
    "pagamento_tot",
    "payment_progress_total",
]

TERRITORY_COLUMNS = [
    "territory_id",
    "territory_name",
    "territory_level",
    "projects_count",
    "weighted_projects_count",
    "finanziamento_pnrr_allocated",
    "pagamento_pnrr_allocated",
    "payment_progress_pnrr_allocated",
    "finanziamento_totale_allocated",
    "pagamento_tot_allocated",
    "payment_progress_total_allocated",
]

PROJECT_COLUMNS = [
    "project_key",
    "cup",
    "codice_locale_progetto",
    "titolo",
    "finanziamento_pnrr",
    "pagamento_pnrr",
    "payment_progress_pnrr",
    "finanziamento_totale",
    "pagamento_tot",
    "payment_progress_total",
    "data_aggiornamento",
]

NUMERIC_COLUMNS = [
    "projects_count",
    "weighted_projects_count",
    "finanziamento_pnrr",
    "pagamento_pnrr",
    "payment_progress_pnrr",
    "finanziamento_totale",
    "pagamento_tot",
    "payment_progress_total",
    "finanziamento_pnrr_allocated",
    "pagamento_pnrr_allocated",
    "payment_progress_pnrr_allocated",
    "finanziamento_totale_allocated",
    "pagamento_tot_allocated",
    "payment_progress_total_allocated",
]


def load_table(input_dir: Path, filename: str) -> pd.DataFrame:
    """Legge una tabella indicatori se esiste, altrimenti restituisce un DataFrame vuoto."""
    path = input_dir / filename
    if not path.exists():
        return pd.DataFrame()
    return read_csv(path)


def select_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Restituisce solo le colonne disponibili tra quelle richieste."""
    available = [column for column in columns if column in df.columns]
    return df[available].copy() if available else pd.DataFrame()


def coerce_dashboard_numbers(df: pd.DataFrame) -> pd.DataFrame:
    """Converte e arrotonda colonne numeriche per ridurre peso e rumore visuale."""
    output = df.copy()
    digits = int(DASHBOARD_SETTINGS["round_digits"])
    for column in NUMERIC_COLUMNS:
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce").round(digits)
    return output


def top_rows(df: pd.DataFrame, sort_column: str, n_rows: int) -> pd.DataFrame:
    """Ordina una tabella per colonna numerica e restituisce le prime righe."""
    if df.empty or sort_column not in df.columns:
        return df
    output = df.copy()
    output[sort_column] = pd.to_numeric(output[sort_column], errors="coerce")
    return output.sort_values(sort_column, ascending=False).head(n_rows)


def records(df: pd.DataFrame) -> list[dict]:
    """Converte un DataFrame in record JSON, sostituendo i mancanti con None."""
    if df.empty:
        return []
    clean = df.where(pd.notna(df), None)
    return clean.to_dict(orient="records")


def write_compact_json(data: dict, path: Path) -> None:
    """Salva un JSON compatto, senza indentazione, per uso front-end."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, separators=(",", ":"), default=str)


def export_dashboard_data(snapshot: str | None = None) -> Path:
    """Crea il JSON leggero della dashboard e restituisce la cartella prodotta."""
    if not SAVE_DASHBOARD_JSON:
        raise RuntimeError("SAVE_DASHBOARD_JSON è False in scripts/config.py")

    snapshot_name = snapshot or latest_snapshot(INDICATORS_DATA_DIR)
    input_dir = INDICATORS_DATA_DIR / snapshot_name
    output_dir = DASHBOARD_DATA_DIR / snapshot_name
    output_dir.mkdir(parents=True, exist_ok=True)

    national = coerce_dashboard_numbers(select_columns(load_table(input_dir, "national_summary.csv"), NATIONAL_COLUMNS))
    regional = coerce_dashboard_numbers(select_columns(load_table(input_dir, "regional_summary.csv"), TERRITORY_COLUMNS))
    province_like = coerce_dashboard_numbers(select_columns(load_table(input_dir, "province_and_metropolitan_city_summary.csv"), TERRITORY_COLUMNS))
    municipal = coerce_dashboard_numbers(select_columns(load_table(input_dir, "municipal_summary.csv"), TERRITORY_COLUMNS))
    projects = coerce_dashboard_numbers(select_columns(load_table(input_dir, "projects_payments.csv"), PROJECT_COLUMNS))

    municipal = top_rows(municipal, "finanziamento_pnrr_allocated", int(DASHBOARD_SETTINGS["top_municipalities"]))
    projects = top_rows(projects, "finanziamento_pnrr", int(DASHBOARD_SETTINGS["top_projects"]))

    payload = {
        "metadata": {
            "snapshot": snapshot_name,
            "generated_at_utc": utc_now_iso(),
            "description": "Dataset compatto per dashboard PNRR. Non contiene raw data completi.",
        },
        "national": records(national),
        "regions": records(regional),
        "province_and_metropolitan_cities": records(province_like),
        "top_municipalities": records(municipal),
        "top_projects": records(projects),
    }

    json_path = output_dir / DASHBOARD_SETTINGS["dashboard_json_filename"]
    write_compact_json(payload, json_path)
    write_csv(regional, output_dir / "dashboard_regions.csv")
    write_csv(municipal, output_dir / "dashboard_top_municipalities.csv")

    manifest = {
        "snapshot": snapshot_name,
        "generated_at_utc": utc_now_iso(),
        "dashboard_json": str(json_path),
        "dashboard_json_bytes": json_path.stat().st_size,
        "regional_rows": len(regional),
        "top_municipality_rows": len(municipal),
        "top_project_rows": len(projects),
    }
    save_json(manifest, output_dir / DASHBOARD_SETTINGS["dashboard_manifest_filename"])
    return output_dir


def main() -> None:
    """Esporta il dataset dashboard sullo snapshot indicatori più recente."""
    output_dir = export_dashboard_data()
    print(f"Dati dashboard salvati in: {output_dir}")


if __name__ == "__main__":
    main()
