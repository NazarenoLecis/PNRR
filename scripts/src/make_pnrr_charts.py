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
from scripts.utils import latest_snapshot, read_csv


def save_horizontal_bar_chart(df: pd.DataFrame, value_column: str, label_column: str, title: str, output_path: str | Path, top_n: int) -> None:
    """Riceve dati, colonne e percorso, salva un grafico a barre orizzontali e non restituisce valori."""
    if df.empty or value_column not in df.columns or label_column not in df.columns:
        return
    plot_df = df[[label_column, value_column]].copy()
    plot_df[value_column] = pd.to_numeric(plot_df[value_column], errors="coerce")
    plot_df = plot_df.dropna(subset=[value_column]).sort_values(value_column, ascending=False).head(top_n)
    plot_df = plot_df.sort_values(value_column, ascending=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(CHART_SETTINGS["figure_width"], CHART_SETTINGS["figure_height"]))
    plt.barh(plot_df[label_column], plot_df[value_column])
    plt.title(title)
    plt.xlabel(value_column)
    plt.tight_layout()
    plt.savefig(output_path, dpi=CHART_SETTINGS["dpi"])
    plt.close()


def make_pnrr_charts(snapshot: str | None = None) -> Path:
    """Riceve uno snapshot indicatori, salva i grafici standard e restituisce la cartella charts."""
    snapshot_name = snapshot or latest_snapshot(INDICATORS_DATA_DIR)
    input_dir = INDICATORS_DATA_DIR / snapshot_name
    output_dir = OUTPUT_CHARTS_DIR / snapshot_name
    output_dir.mkdir(parents=True, exist_ok=True)
    regional = read_csv(input_dir / "regional_summary.csv")
    municipal = read_csv(input_dir / "municipal_summary.csv")
    save_horizontal_bar_chart(regional, "finanziamento_pnrr_allocated", "territory_name", "Prime regioni per finanziamento PNRR allocato", output_dir / "top_regions_by_pnrr_funding.png", CHART_SETTINGS["top_n_regions"])
    save_horizontal_bar_chart(regional, "payment_progress_pnrr_allocated", "territory_name", "Prime regioni per avanzamento finanziario PNRR", output_dir / "top_regions_by_payment_progress.png", CHART_SETTINGS["top_n_regions"])
    save_horizontal_bar_chart(municipal, "finanziamento_pnrr_allocated", "territory_name", "Primi comuni per finanziamento PNRR allocato", output_dir / "top_municipalities_by_pnrr_funding.png", CHART_SETTINGS["top_n_municipalities"])
    return output_dir


def main() -> None:
    """Genera i grafici sullo snapshot indicatori più recente e non restituisce valori."""
    output_dir = make_pnrr_charts()
    print(f"Grafici salvati in: {output_dir}")


if __name__ == "__main__":
    main()
