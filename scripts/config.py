"""Configurazioni centrali del progetto PNRR.

Il file contiene percorsi, URL, nomi dei file, parametri modificabili e
costanti metodologiche usate da script e notebook. Le modifiche operative
vanno fatte qui, evitando percorsi o URL scritti direttamente nel codice.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DATA_DIR = PROJECT_ROOT / "output" / "data"
OUTPUT_CHARTS_DIR = PROJECT_ROOT / "output" / "charts"
RAW_DATA_DIR = OUTPUT_DATA_DIR / "raw"
CLEAN_DATA_DIR = OUTPUT_DATA_DIR / "clean"
INDICATORS_DATA_DIR = OUTPUT_DATA_DIR / "indicators"

DEFAULT_SNAPSHOT = date.today().isoformat()
ANALYSIS_YEARS = list(range(2021, 2031))

OPENPNRR_CSV_BASE_URL = "https://openpnrr.it/csv"
OPENPNRR_MEDIA_BASE_URL = "https://openpnrr.s3.amazonaws.com/media"
OPENPNRR_LANDING_PAGE = "https://openpnrr.it/opendata/"
OPENPNRR_METADATA_PAGE = "https://openpnrr.it/metadati/"
ITALIA_DOMANI_OPEN_DATA_PAGE = "https://www.italiadomani.gov.it/it/catalogo-open-data.html"
ANAC_OPEN_DATA_PAGE = "https://dati.anticorruzione.it/opendata"
OPENCUP_PAGE = "https://www.opencup.gov.it/"
ISTAT_TERRITORIAL_CODES_PAGE = "https://www.istat.it/it/archivio/6789"

# Il download salva sempre i CSV grezzi. Se SAVE_RAW_JSON è True salva anche
# una versione JSON per ogni tabella scaricata o generata come fallback tecnico.
SAVE_RAW_JSON = True
SAVE_CLEAN_JSON = True
ALLOW_SAMPLE_FALLBACK = True
DOWNLOAD_TIMEOUT_SECONDS = 60
DOWNLOAD_RETRIES = 1
DOWNLOAD_USER_AGENT = "PNRR analysis repository"

OPENPNRR_SOURCES = {
    "missions": {"url": f"{OPENPNRR_CSV_BASE_URL}/missioni.csv", "raw_filename": "openpnrr_missions.csv"},
    "components": {"url": f"{OPENPNRR_CSV_BASE_URL}/componenti.csv", "raw_filename": "openpnrr_components.csv"},
    "measures": {"url": f"{OPENPNRR_CSV_BASE_URL}/misure.csv", "raw_filename": "openpnrr_measures.csv"},
    "deadlines": {"url": f"{OPENPNRR_CSV_BASE_URL}/scadenze.csv", "raw_filename": "openpnrr_deadlines.csv"},
    "organizations": {"url": f"{OPENPNRR_CSV_BASE_URL}/organizzazioni.csv", "raw_filename": "openpnrr_organizations.csv"},
    "territories": {"url": f"{OPENPNRR_CSV_BASE_URL}/territori.csv", "raw_filename": "openpnrr_territories.csv", "clean_filename": "territories.csv"},
    "themes": {"url": f"{OPENPNRR_CSV_BASE_URL}/temi.csv", "raw_filename": "openpnrr_themes.csv"},
    "priorities": {"url": f"{OPENPNRR_CSV_BASE_URL}/priorita.csv", "raw_filename": "openpnrr_priorities.csv"},
    "projects": {"url": f"{OPENPNRR_MEDIA_BASE_URL}/progetti.csv", "raw_filename": "openpnrr_projects.csv", "clean_filename": "projects.csv"},
    "locations": {"url": f"{OPENPNRR_MEDIA_BASE_URL}/progetti_territori.csv", "raw_filename": "openpnrr_project_locations.csv", "clean_filename": "locations.csv"},
    "payments": {"url": f"{OPENPNRR_MEDIA_BASE_URL}/progetti_pagamenti.csv", "raw_filename": "openpnrr_project_payments.csv", "clean_filename": "payments.csv"},
    "procurement": {"url": f"{OPENPNRR_MEDIA_BASE_URL}/cig_gare-pnrr.csv", "raw_filename": "openpnrr_procurement_cig.csv"},
}

CORE_TABLES = ["projects", "payments", "locations", "territories"]

FUNDING_COLUMNS = [
    "finanziamento_pnrr",
    "finanziamento_regione",
    "finanziamento_provincia",
    "finanziamento_comune",
    "finanziamento_altro_pubblico",
    "finanziamento_privato",
    "finanziamento_da_reperire",
    "finanziamento_pnc",
    "finanziamento_totale",
    "finanziamento_ue_no_pnrr",
    "finanziamento_altri_fondi",
    "finanziamento_totale_pubblico",
]

PAYMENT_COLUMNS = [
    "pagamento_tot",
    "pagamento_pnrr",
    "pagamento_foi",
    "pagamento_fpop",
    "pagamento_ue",
    "pagamento_regione",
    "pagamento_prov",
    "pagamento_comune",
    "pagamento_altro_pubblico",
    "pagamento_privato",
    "pagamento_da_reperire",
    "pagamento_pnc",
    "pagamento_altri_fondi",
]

TERRITORY_PRIORITY = {"C": 4, "CM": 3, "P": 2, "R": 1}

TERRITORY_OUTPUT_FILES = {
    "R": "regional_summary.csv",
    "P": "province_summary.csv",
    "CM": "metropolitan_city_summary.csv",
    "C": "municipal_summary.csv",
}

CHART_SETTINGS = {
    "figure_width": 10,
    "figure_height": 6,
    "dpi": 150,
    "top_n_regions": 15,
    "top_n_municipalities": 25,
}

PIPELINE_DIRECTORIES = [
    OUTPUT_DATA_DIR,
    OUTPUT_CHARTS_DIR,
    RAW_DATA_DIR,
    CLEAN_DATA_DIR,
    INDICATORS_DATA_DIR,
]
