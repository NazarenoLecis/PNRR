# PNRR

Repository per analizzare gli open data sul Piano nazionale di ripresa e resilienza a livello nazionale, regionale, provinciale e comunale.

L'obiettivo è costruire una pipeline leggibile e ripetibile per capire dove ricadono i progetti, quali importi risultano finanziati, quali pagamenti risultano registrati e come cambiano gli indicatori tra territori.

## Struttura

```text
repo/
  README.md
  requirements.txt

  scripts/
    config.py
    utils.py
    src/
      download_pnrr_data.py
      clean_pnrr_projects.py
      build_pnrr_indicators.py
      make_pnrr_charts.py
      run_pnrr_pipeline.py

  notebooks/
    01_data_quality_checks.ipynb
    02_national_regional_analysis.ipynb
    03_municipal_focus.ipynb
    04_final_charts.ipynb

  output/
    data/
    charts/
```

`scripts/config.py` contiene percorsi, URL, parametri, colonne monetarie, livelli territoriali e costanti metodologiche.

`scripts/utils.py` contiene funzioni riutilizzabili per lettura, scrittura, JSON, normalizzazione, conversione importi e chiavi tecniche.

`scripts/src` contiene il codice operativo.

`notebooks` contiene notebook numerati con parametri modificabili, spiegazioni e controlli.

## Fonti dati

La fonte operativa iniziale è OpenPNRR.

- Open data: https://openpnrr.it/opendata/
- Metadati: https://openpnrr.it/metadati/

La configurazione include missioni, componenti, misure, scadenze, organizzazioni, territori, temi, priorità, progetti, localizzazioni, pagamenti e CIG/gare PNRR.

Gli URL sono definiti in `OPENPNRR_SOURCES` dentro `scripts/config.py`.

## Installazione

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Su Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Esecuzione

Run completo:

```bash
python scripts/src/run_pnrr_pipeline.py
```

Run per fasi:

```bash
python scripts/src/download_pnrr_data.py
python scripts/src/clean_pnrr_projects.py
python scripts/src/build_pnrr_indicators.py
python scripts/src/make_pnrr_charts.py
```

## Parametri principali

I parametri sono centralizzati in `scripts/config.py`.

- `SAVE_RAW_JSON` salva ogni fonte grezza anche in JSON.
- `SAVE_CLEAN_JSON` salva le tabelle pulite anche in JSON.
- `ALLOW_SAMPLE_FALLBACK` abilita un piccolo campione tecnico se il download remoto non è disponibile.
- `DOWNLOAD_TIMEOUT_SECONDS` definisce il timeout HTTP.
- `FUNDING_COLUMNS` e `PAYMENT_COLUMNS` definiscono le colonne monetarie.
- `TERRITORY_PRIORITY` definisce la priorità territoriale: comune, città metropolitana, provincia, regione.
- `CHART_SETTINGS` controlla dimensione grafici e numero di elementi nei ranking.

Per lavorare solo su dati reali, impostare `ALLOW_SAMPLE_FALLBACK = False`.

## Output

Dati grezzi in `output/data/raw/<snapshot>/`.

```text
openpnrr_*.csv
openpnrr_*.json
manifest.json
```

Dati puliti in `output/data/clean/<snapshot>/`.

```text
projects.csv
projects.json
payments.csv
payments.json
locations.csv
locations.json
territories.csv
territories.json
cleaning_report.csv
cleaning_report.json
```

Indicatori in `output/data/indicators/<snapshot>/`.

```text
projects_payments.csv
projects_payments.json
territory_projects.csv
territory_projects.json
national_summary.csv
national_summary.json
regional_summary.csv
regional_summary.json
province_summary.csv
province_summary.json
metropolitan_city_summary.csv
metropolitan_city_summary.json
municipal_summary.csv
municipal_summary.json
run_summary.json
```

Grafici in `output/charts/<snapshot>/`.

```text
top_regions_by_pnrr_funding.png
top_regions_by_payment_progress.png
top_municipalities_by_pnrr_funding.png
charts_manifest.json
```

## Definizioni

`finanziamento_pnrr` indica l'importo finanziato con risorse PNRR quando la colonna è disponibile.

`pagamento_pnrr` indica i pagamenti PNRR cumulati registrati nel dataset dei pagamenti.

`payment_progress_pnrr` è il rapporto tra `pagamento_pnrr` e `finanziamento_pnrr`.

`project_key` è la chiave tecnica usata per collegare progetti, pagamenti e localizzazioni. La pipeline usa prima l'identificativo progetto esplicito. Se manca, usa CUP e codice locale progetto.

`allocation_weight_equal` è il peso usato per ripartire gli importi tra più localizzazioni selezionate dello stesso progetto.

Le colonne con suffisso `_allocated` contengono importi territorialmente allocati.

## Metodologia

La pipeline salva uno snapshot locale dei dati. Il nome dello snapshot coincide con la data di lavorazione se non viene indicato un nome diverso.

Il download genera CSV e JSON. Il manifest indica per ogni fonte se il dato è stato scaricato o se è stato usato il fallback campione.

La pulizia normalizza nomi colonna, identificativi e importi. I pagamenti vengono aggregati per progetto prima del join.

Le localizzazioni vengono arricchite con l'anagrafica dei territori. Per ogni progetto viene scelto il livello territoriale più fine disponibile. Se un progetto ha più localizzazioni allo stesso livello selezionato, gli importi sono ripartiti in quote uguali.

Gli indicatori nazionali usano progetti non duplicati. Gli indicatori territoriali usano importi allocati.

## Assunzioni e limiti

Il dataset dei pagamenti viene interpretato come stock cumulato alla data di aggiornamento disponibile nella fonte.

La data dello snapshot locale indica quando i dati sono stati scaricati. Non coincide necessariamente con la data amministrativa del pagamento.

Il riparto uniforme è una convenzione analitica. Non stima il riparto amministrativo effettivo quando la fonte non pubblica quote territoriali specifiche.

Il repository non ricostruisce ogni passaggio contabile al dettaglio di fattura o mandato.

Gli indicatori pro capite richiedono una fonte demografica aggiuntiva, per esempio ISTAT.

## Lettura dei risultati

`national_summary.csv` descrive il quadro nazionale senza duplicazione territoriale.

`regional_summary.csv` confronta le regioni per finanziamenti, pagamenti e avanzamento finanziario allocato.

`municipal_summary.csv` permette analisi comunali sui soli progetti localizzati a livello comunale.

Un avanzamento finanziario alto indica maggiore quota pagata rispetto al finanziamento registrato. Non misura direttamente avanzamento fisico, qualità amministrativa o impatto economico.
