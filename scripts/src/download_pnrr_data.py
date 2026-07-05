"""Download dei dati OpenPNRR in cartelle snapshot."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.config import DEFAULT_SNAPSHOT, OPENPNRR_SOURCES, PIPELINE_DIRECTORIES, RAW_DATA_DIR
from scripts.utils import download_file, ensure_directories, save_json, utc_now_iso


def download_pnrr_data(snapshot: str | None = None, overwrite: bool = False) -> Path:
    """Riceve snapshot e overwrite, scarica i CSV configurati e restituisce la cartella raw."""
    ensure_directories(PIPELINE_DIRECTORIES)
    snapshot_name = snapshot or DEFAULT_SNAPSHOT
    snapshot_dir = RAW_DATA_DIR / snapshot_name
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    downloaded_files = []
    for source_name, source in OPENPNRR_SOURCES.items():
        destination = snapshot_dir / source["raw_filename"]
        metadata = download_file(source["url"], destination, overwrite=overwrite)
        metadata["source_name"] = source_name
        downloaded_files.append(metadata)
    save_json({"snapshot": snapshot_name, "downloaded_at_utc": utc_now_iso(), "sources": downloaded_files}, snapshot_dir / "manifest.json")
    return snapshot_dir


def main() -> None:
    """Esegue il download con configurazione standard e non restituisce valori."""
    snapshot_dir = download_pnrr_data()
    print(f"Dati scaricati in: {snapshot_dir}")


if __name__ == "__main__":
    main()
