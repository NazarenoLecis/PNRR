"""Generazione dei grafici PNRR da tabelle indicatore."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.config import CHART_SETTINGS, INDICATORS_DATA_DIR, OUTPUT_CHARTS_DIR
from scripts.utils import latest_snapshot, read_csv, save_json


def save_horizontal_bar_chart(df: pd.DataFrame, value_column: str, label_column: str, title: str, output_path: str | Path, top_n: int) -> Path | None:
    """Salva un grafico a barre orizzontali e restituisce il percorso generato."""
    if df.empty or value_column not in df.columns or label_column not in df.columns:
        return None
    plot_df = df[[label_column, value_column]].copy()
    plot_df[value_column] = pd.to_numeric(plot_df[value_column], errors="coerce")
    plot_df = plot_df.dropna(subset=[value_column]).sort_values(value_column, ascending=False).head(top_n)
    if plot_df.empty:
        return None
    plot_df = plot_df.sort_values(value_column, ascending=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(CHART_SETTINGS["figure_width"], CHART_SETTINGS["figure_height"]))
    plt.barh(plot_df[label_column].astype(str), plot_df[value_column])
    plt.title(title)
    plt.xlabel(value_column)
    plt.tight_layout()
    plt.savefig(output_path, dpi=CHART_SETTINGS["dpi"], bbox_inches="tight")
    plt.close()
    return output_path


def make_pnrr_charts(snapshot: str | None = None) -> Path:
    """Salva i grafici standard e un manifest JSON nella cartella charts."""
    snapshot_name = snapshot or latest_snapshot(INDICATORS_DATA_DIR)
    input_dir = INDICATORS_DATA_DIR / snapshot_name
    output_dir = OUTPUT_CHARTS_DIR / snapshot_name
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []

    regional_path = input_dir / "regional_summary.csv"
    if regional_path.exists():
        regional = read_csv(regional_path)
        path = save_horizontal_bar_chart(regional, "finanziamento_pnrr_allocated", "territory_name", "Prime regioni per finanziamento PNRR allocato", output_dir / "top_regions_by_pnrr_funding.png", CHART_SETTINGS["top_n_regions"])
        if path is not None:
            generated.append(str(path))
        path = save_horizontal_bar_chart(regional, "payment_progress_pnrr_allocated", "territory_name", "Prime regioni per avanzamento finanziario PNRR", output_dir / "top_regions_by_payment_progress.png", CHART_SETTINGS["top_n_regions"])
        if path is not None:
            generated.append(str(path))

    municipal_path = input_dir / "municipal_summary.csv"
    if municipal_path.exists():
        municipal = read_csv(municipal_path)
        path = save_horizontal_bar_chart(municipal, "finanziamento_pnrr_allocated", "territory_name", "Primi comuni per finanziamento PNRR allocato", output_dir / "top_municipalities_by_pnrr_funding.png", CHART_SETTINGS["top_n_municipalities"])
        if path is not None:
            generated.append(str(path))

    save_json({"snapshot": snapshot_name, "generated_charts": generated}, output_dir / "charts_manifest.json")
    return output_dir


def main() -> None:
    """Genera i grafici sullo snapshot indicatori più recente."""
    output_dir = make_pnrr_charts()
    print(f"Grafici salvati in: {output_dir}")


if __name__ == "__main__":
    main()
