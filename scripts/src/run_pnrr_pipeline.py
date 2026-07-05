"""Esecuzione completa della pipeline PNRR."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.src.build_pnrr_indicators import build_pnrr_indicators
from scripts.src.clean_pnrr_projects import build_clean_pnrr_tables
from scripts.src.download_pnrr_data import download_pnrr_data
from scripts.src.make_pnrr_charts import make_pnrr_charts


def run_pnrr_pipeline(snapshot: str | None = None, overwrite: bool = False) -> dict[str, Path]:
    """Riceve snapshot e overwrite, esegue tutta la pipeline e restituisce le cartelle prodotte."""
    raw_dir = download_pnrr_data(snapshot=snapshot, overwrite=overwrite)
    snapshot_name = raw_dir.name
    clean_dir = build_clean_pnrr_tables(snapshot=snapshot_name)
    indicator_dir = build_pnrr_indicators(snapshot=snapshot_name)
    chart_dir = make_pnrr_charts(snapshot=snapshot_name)
    return {"raw": raw_dir, "clean": clean_dir, "indicators": indicator_dir, "charts": chart_dir}


def main() -> None:
    """Esegue la pipeline completa con configurazione standard e non restituisce valori."""
    outputs = run_pnrr_pipeline()
    for step, path in outputs.items():
        print(f"{step}: {path}")


if __name__ == "__main__":
    main()
