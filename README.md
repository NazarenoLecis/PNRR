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
      export_dashboard_data.py
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
python scripts/src/export_dashboard_data.py
python scripts/src/make_pnrr_charts.py
```

## Impostazione leggera per dashboard

La dashboard non deve leggere raw, clean o indicatori completi. Questi file servono all'analisi locale. Il front-end deve usare il file compatto prodotto da:

```bash
python scripts/src/export_dashboard_data.py
```

Il file principale per la dashboard è:

```text
output/data/dashboard/<snapshot>/pnrr_dashboard_data.json
```

Questo JSON contiene solo:

- sintesi nazionale;
- regioni;
- province e città metropolitane;
- primi comuni per finanziamento PNRR allocato;
- primi progetti per finanziamento PNRR.

I limiti dimensionali sono configurati in `DASHBOARD_SETTINGS`.

## Parametri principali

I parametri sono centralizzati in `scripts/config.py`.

- `SAVE_RAW_JSON = False` evita JSON pesanti dei dati grezzi.
- `SAVE_CLEAN_JSON = False` evita JSON pesanti dei dati puliti.
- `SAVE_INDICATOR_JSON = False` evita JSON completi degli indicatori.
- `SAVE_DASHBOARD_JSON = True` genera solo il JSON compatto per dashboard.
- `ALLOW_SAMPLE_FALLBACK` abilita un piccolo campione tecnico se il download remoto non è disponibile.
- `DOWNLOAD_TIMEOUT_SECONDS` definisce il timeout HTTP.
- `FUNDING_COLUMNS` e `PAYMENT_COLUMNS` definiscono le colonne monetarie.
- `TERRITORY_PRIORITY` definisce la priorità territoriale: comune, città metropolitana, provincia, regione.
- `DASHBOARD_SETTINGS` definisce numero massimo di comuni e progetti esportati nella dashboard.
- `CHART_SETTINGS` controlla dimensione grafici e numero di elementi nei ranking.

Per lavorare solo su dati reali, impostare `ALLOW_SAMPLE_FALLBACK = False`.

## Output

Dati grezzi in `output/data/raw/<snapshot>/`.

```text
openpnrr_*.csv
manifest.json
```

Dati puliti in `output/data/clean/<snapshot>/`.

```text
projects.csv
payments.csv
locations.csv
territories.csv
cleaning_report.csv
```

Indicatori completi in `output/data/indicators/<snapshot>/`.

```text
projects_payments.csv
territory_projects.csv
national_summary.csv
regional_summary.csv
province_summary.csv
metropolitan_city_summary.csv
municipal_summary.csv
run_summary.json
```

Dataset compatto per dashboard in `output/data/dashboard/<snapshot>/`.

```text
pnrr_dashboard_data.json
dashboard_regions.csv
dashboard_top_municipalities.csv
dashboard_manifest.json
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

Il download salva i CSV grezzi. I JSON completi sono disattivati di default per evitare output troppo pesanti.

La pulizia normalizza nomi colonna, identificativi e importi. I pagamenti vengono aggregati per progetto prima del join.

Le localizzazioni vengono arricchite con l'anagrafica dei territori. Per ogni progetto viene scelto il livello territoriale più fine disponibile. Se un progetto ha più localizzazioni allo stesso livello selezionato, gli importi sono ripartiti in quote uguali.

Gli aggregati comunali usano le localizzazioni comunali selezionate. Gli aggregati provinciali, di città metropolitana e regionali sono costruiti con roll-up gerarchico dai territori selezionati verso i rispettivi territori padre.

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

`pnrr_dashboard_data.json` è il file da servire alla dashboard. Gli altri output sono file di lavoro e controllo.

Un avanzamento finanziario alto indica maggiore quota pagata rispetto al finanziamento registrato. Non misura direttamente avanzamento fisico, qualità amministrativa o impatto economico.
