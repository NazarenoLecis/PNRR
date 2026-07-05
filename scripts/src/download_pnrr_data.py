"""Download dei dati OpenPNRR in cartelle snapshot.

Lo script salva ogni tabella grezza in CSV e JSON. Quando l'ambiente non
raggiunge la rete e `ALLOW_SAMPLE_FALLBACK` è attivo, genera un piccolo
campione tecnico per validare pipeline e notebook.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.config import (
    ALLOW_SAMPLE_FALLBACK,
    DEFAULT_SNAPSHOT,
    DOWNLOAD_RETRIES,
    DOWNLOAD_TIMEOUT_SECONDS,
    DOWNLOAD_USER_AGENT,
    OPENPNRR_SOURCES,
    PIPELINE_DIRECTORIES,
    RAW_DATA_DIR,
    SAVE_RAW_JSON,
)
from scripts.utils import download_file, ensure_directories, read_csv, save_json, utc_now_iso, write_csv, write_json_records


def sample_tables() -> dict[str, pd.DataFrame]:
    """Restituisce tabelle campione coerenti con la pipeline.

    Il campione serve solo per test tecnici in ambienti senza accesso internet.
    Non rappresenta dati empirici sul PNRR.
    """
    return {
        "projects": pd.DataFrame(
            [
                {"id": "P001", "cup": "C11B22000100006", "codice_locale_progetto": "CLP001", "titolo": "Migrazione servizi cloud", "finanziamento_pnrr": 1200000, "finanziamento_totale": 1400000, "finanziamento_totale_pubblico": 1400000},
                {"id": "P002", "cup": "D45F22000200006", "codice_locale_progetto": "CLP002", "titolo": "Piattaforma digitale comunale", "finanziamento_pnrr": 850000, "finanziamento_totale": 900000, "finanziamento_totale_pubblico": 900000},
                {"id": "P003", "cup": "E81B21000300001", "codice_locale_progetto": "CLP003", "titolo": "Messa in sicurezza idrogeologica", "finanziamento_pnrr": 5000000, "finanziamento_totale": 5600000, "finanziamento_totale_pubblico": 5500000},
                {"id": "P004", "cup": "F32C22000400002", "codice_locale_progetto": "CLP004", "titolo": "Rigenerazione urbana", "finanziamento_pnrr": 2300000, "finanziamento_totale": 2500000, "finanziamento_totale_pubblico": 2500000},
            ]
        ),
        "payments": pd.DataFrame(
            [
                {"progetto_id": "P001", "pagamento_tot": 420000, "pagamento_pnrr": 400000, "data_aggiornamento": "2026-02-26"},
                {"progetto_id": "P002", "pagamento_tot": 250000, "pagamento_pnrr": 240000, "data_aggiornamento": "2026-02-26"},
                {"progetto_id": "P003", "pagamento_tot": 1250000, "pagamento_pnrr": 1200000, "data_aggiornamento": "2026-02-26"},
                {"progetto_id": "P004", "pagamento_tot": 500000, "pagamento_pnrr": 480000, "data_aggiornamento": "2026-02-26"},
            ]
        ),
        "locations": pd.DataFrame(
            [
                {"progetto_id": "P001", "territorio_id": "111"},
                {"progetto_id": "P002", "territorio_id": "211"},
                {"progetto_id": "P003", "territorio_id": "311"},
                {"progetto_id": "P004", "territorio_id": "111"},
                {"progetto_id": "P004", "territorio_id": "211"},
            ]
        ),
        "territories": pd.DataFrame(
            [
                {"id": "100", "istat_id": "01", "tipologia": "R", "denominazione": "Piemonte", "parent_id": ""},
                {"id": "200", "istat_id": "03", "tipologia": "R", "denominazione": "Lombardia", "parent_id": ""},
                {"id": "300", "istat_id": "12", "tipologia": "R", "denominazione": "Lazio", "parent_id": ""},
                {"id": "110", "istat_id": "001", "tipologia": "CM", "denominazione": "Torino", "parent_id": "100"},
                {"id": "210", "istat_id": "015", "tipologia": "CM", "denominazione": "Milano", "parent_id": "200"},
                {"id": "310", "istat_id": "058", "tipologia": "CM", "denominazione": "Roma", "parent_id": "300"},
                {"id": "111", "istat_id": "001272", "tipologia": "C", "denominazione": "Torino", "parent_id": "110"},
                {"id": "211", "istat_id": "015146", "tipologia": "C", "denominazione": "Milano", "parent_id": "210"},
                {"id": "311", "istat_id": "058091", "tipologia": "C", "denominazione": "Roma", "parent_id": "310"},
            ]
        ),
        "missions": pd.DataFrame([{"id": "1", "codice": "M1", "descr": "Digitalizzazione"}]),
        "components": pd.DataFrame([{"id": "11", "missione_id": "1", "codice": "M1C1", "descr": "Digitalizzazione PA"}]),
        "measures": pd.DataFrame([{"id": "101", "componente_id": "11", "codice_misura": "1.2", "descrizione": "Abilitazione al cloud"}]),
        "deadlines": pd.DataFrame([{"id": "9001", "tipologia": "M", "descrizione_breve": "Scadenza campione"}]),
        "organizations": pd.DataFrame([{"id": "501", "denominazione": "Comune campione"}]),
        "themes": pd.DataFrame([{"id": "t1", "descrizione": "Tema campione"}]),
        "priorities": pd.DataFrame([{"id": "p1", "descrizione": "Priorità campione"}]),
        "procurement": pd.DataFrame([{"progetto_id": "P001", "cig": "9000000001", "importo_gara": 700000}]),
    }


def network_available() -> bool:
    """Verifica in modo leggero se il dominio OpenPNRR è risolvibile."""
    try:
        socket.gethostbyname("openpnrr.it")
    except OSError:
        return False
    return True


def save_raw_table(df: pd.DataFrame, destination: Path) -> None:
    """Salva una tabella grezza in CSV e JSON con lo stesso nome base."""
    write_csv(df, destination)
    if SAVE_RAW_JSON:
        write_json_records(df, destination.with_suffix(".json"))


def download_pnrr_data(snapshot: str | None = None, overwrite: bool = False) -> Path:
    """Scarica i CSV configurati, genera JSON e restituisce la cartella raw.

    Args:
        snapshot: nome snapshot. Se None usa la data corrente.
        overwrite: se True riscarica file già presenti.

    Returns:
        Percorso della cartella raw dello snapshot.
    """
    ensure_directories(PIPELINE_DIRECTORIES)
    snapshot_name = snapshot or DEFAULT_SNAPSHOT
    snapshot_dir = RAW_DATA_DIR / snapshot_name
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    samples = sample_tables()
    use_sample_only = ALLOW_SAMPLE_FALLBACK and not network_available()
    downloaded_files = []

    for source_name, source in OPENPNRR_SOURCES.items():
        destination = snapshot_dir / source["raw_filename"]
        try:
            if use_sample_only:
                raise RuntimeError("network_precheck_failed")
            metadata = download_file(
                source["url"],
                destination,
                overwrite=overwrite,
                timeout=DOWNLOAD_TIMEOUT_SECONDS,
                user_agent=DOWNLOAD_USER_AGENT,
            )
            df = read_csv(destination)
            save_raw_table(df, destination)
        except Exception as exc:
            if not ALLOW_SAMPLE_FALLBACK or source_name not in samples:
                metadata = {"url": source["url"], "path": str(destination), "status": "failed", "error": str(exc)}
                downloaded_files.append({"source_name": source_name, **metadata})
                continue
            df = samples[source_name]
            save_raw_table(df, destination)
            metadata = {"url": source["url"], "path": str(destination), "status": "sample_fallback", "rows": len(df), "error": str(exc)}
        metadata["source_name"] = source_name
        metadata["json_path"] = str(destination.with_suffix(".json")) if SAVE_RAW_JSON else ""
        downloaded_files.append(metadata)

    save_json({"snapshot": snapshot_name, "downloaded_at_utc": utc_now_iso(), "sources": downloaded_files}, snapshot_dir / "manifest.json")
    return snapshot_dir


def main() -> None:
    """Esegue il download con configurazione standard."""
    snapshot_dir = download_pnrr_data()
    print(f"Dati scaricati in: {snapshot_dir}")


if __name__ == "__main__":
    main()
