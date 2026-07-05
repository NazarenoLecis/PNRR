"""Funzioni generali riutilizzabili per il progetto PNRR."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


def ensure_directories(paths: Iterable[str | Path]) -> None:
    """Crea le cartelle indicate in input e non restituisce valori."""
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
    """Restituisce il timestamp UTC corrente in formato ISO."""
    return datetime.now(UTC).isoformat()


def hash_file(path: str | Path) -> str:
    """Riceve un percorso file e restituisce l'hash SHA-256."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_json(data: dict | list, path: str | Path) -> None:
    """Riceve dati serializzabili e un percorso, salva un JSON formattato."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False, default=str)


def write_json_records(df: pd.DataFrame, path: str | Path) -> None:
    """Riceve un DataFrame e salva un JSON orientato a lista di record."""
    records = df.where(pd.notna(df), None).to_dict(orient="records")
    save_json(records, path)


def download_file(url: str, destination: str | Path, overwrite: bool = False, timeout: int = 60, user_agent: str | None = None) -> dict:
    """Scarica un URL in un percorso locale e restituisce metadati del file salvato.

    Args:
        url: risorsa remota.
        destination: percorso locale.
        overwrite: se True riscarica anche se il file esiste.
        timeout: timeout HTTP in secondi.
        user_agent: intestazione User-Agent opzionale.

    Returns:
        Dizionario con stato, byte e hash del file.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not overwrite:
        return {"url": url, "path": str(destination), "status": "skipped_existing", "bytes": destination.stat().st_size, "sha256": hash_file(destination)}
    temporary_path = destination.with_suffix(destination.suffix + ".tmp")
    headers = {"User-Agent": user_agent} if user_agent else None
    with requests.get(url, stream=True, timeout=timeout, headers=headers) as response:
        response.raise_for_status()
        with temporary_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    temporary_path.replace(destination)
    return {"url": url, "path": str(destination), "status": "downloaded", "bytes": destination.stat().st_size, "sha256": hash_file(destination)}


def read_csv(path: str | Path) -> pd.DataFrame:
    """Riceve un percorso CSV e restituisce un DataFrame con identificativi letti come stringhe."""
    return pd.read_csv(Path(path), sep=None, engine="python", dtype="string", encoding="utf-8-sig", keep_default_na=False, na_values=[""])


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    """Riceve un DataFrame e un percorso, salva un CSV UTF-8."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(destination, index=False, encoding="utf-8")


def write_table_outputs(df: pd.DataFrame, csv_path: str | Path, save_json_output: bool = True) -> None:
    """Salva una tabella in CSV e, se richiesto, anche in JSON.

    La funzione usa lo stesso nome base del CSV e sostituisce l'estensione con
    `.json`. Serve a mantenere paralleli output tabellari e output JSON.
    """
    csv_path = Path(csv_path)
    write_csv(df, csv_path)
    if save_json_output:
        write_json_records(df, csv_path.with_suffix(".json"))


def normalize_column_name(name: object) -> str:
    """Riceve un nome colonna grezzo e restituisce un nome snake_case ASCII."""
    normalized = unicodedata.normalize("NFKD", str(name))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Riceve un DataFrame e restituisce una copia con colonne normalizzate."""
    output = df.copy()
    output.columns = [normalize_column_name(column) for column in output.columns]
    return output


def clean_string(value: object) -> str | pd.NA:
    """Riceve un valore generico e restituisce una stringa pulita o un valore mancante."""
    if pd.isna(value):
        return pd.NA
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "<na>"}:
        return pd.NA
    return text


def clean_code(value: object) -> str | pd.NA:
    """Riceve un identificativo e restituisce una stringa maiuscola pulita o un valore mancante."""
    text = clean_string(value)
    if pd.isna(text):
        return pd.NA
    return str(text).replace(".0", "").upper()


def normalize_numeric_text(value: object) -> str | pd.NA:
    """Riceve testo numerico italiano o inglese e restituisce una stringa decimale standard."""
    if pd.isna(value):
        return pd.NA
    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not text:
        return pd.NA
    text = re.sub(r"[^0-9,.-]", "", text)
    if text in {"", "-", ",", "."}:
        return pd.NA
    last_comma = text.rfind(",")
    last_dot = text.rfind(".")
    if last_comma > -1 and last_dot > -1:
        if last_comma > last_dot:
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif last_comma > -1:
        text = text.replace(".", "").replace(",", ".")
    return text


def coerce_numeric_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Riceve un DataFrame e colonne candidate, restituisce una copia con colonne numeriche."""
    output = df.copy()
    for column in columns:
        if column in output.columns:
            output[column] = pd.to_numeric(output[column].map(normalize_numeric_text), errors="coerce").fillna(0.0)
    return output


def first_existing_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    """Riceve un DataFrame e colonne candidate, restituisce la prima colonna esistente."""
    for column in candidates:
        if column in df.columns:
            return column
    return None


def add_project_key(df: pd.DataFrame) -> pd.DataFrame:
    """Riceve una tabella PNRR e restituisce una copia con chiave tecnica project_key.

    Criterio metodologico: se esiste un identificativo progetto esplicito
    (`progetto_id`, `id_progetto`, `id`) viene usato come chiave primaria. Se
    manca, la chiave viene costruita con CUP e codice locale progetto. Questa
    scelta riduce il rischio di join mancati tra progetti, pagamenti e
    localizzazioni quando le tabelle pubblicano identificativi diversi.
    """
    output = df.copy()
    id_column = first_existing_column(output, ["progetto_id", "id_progetto", "id"])
    if id_column is not None:
        output["project_key"] = "PROJECT_ID|" + output[id_column].map(clean_code).astype("string").fillna("")
        return output

    cup = output["cup"].map(clean_code).astype("string") if "cup" in output.columns else pd.Series(pd.NA, index=output.index, dtype="string")
    clp = output["codice_locale_progetto"].map(clean_code).astype("string") if "codice_locale_progetto" in output.columns else pd.Series(pd.NA, index=output.index, dtype="string")
    output["cup"] = cup
    output["codice_locale_progetto"] = clp
    key = cup.fillna("") + "|" + clp.fillna("")
    output["project_key"] = key.mask(key.str.strip("|") == "", pd.NA).astype("string")
    return output


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Riceve numeratore e denominatore, restituisce il rapporto con valori mancanti su denominatore zero."""
    num = pd.to_numeric(numerator, errors="coerce")
    den = pd.to_numeric(denominator, errors="coerce")
    return num / den.where(den != 0)


def latest_snapshot(root: str | Path) -> str:
    """Riceve una cartella con snapshot e restituisce il nome dello snapshot più recente."""
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"Cartella snapshot non trovata: {root_path}")
    snapshots = sorted(path.name for path in root_path.iterdir() if path.is_dir())
    if not snapshots:
        raise FileNotFoundError(f"Nessuno snapshot disponibile in {root_path}")
    return snapshots[-1]
