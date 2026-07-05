# PNRR

Questo repository serve ad analizzare i dati aperti sul Piano nazionale di ripresa e resilienza a livello nazionale, regionale e comunale.

L'obiettivo è costruire una pipeline leggibile e ripetibile. Il codice scarica i dati, li pulisce, costruisce indicatori territoriali e salva tabelle e grafici nelle cartelle di output.

## Struttura del repository

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

`scripts/config.py` centralizza percorsi, URL, nomi dei file, colonne monetarie, livelli territoriali, parametri dei grafici e costanti metodologiche.

`scripts/utils.py` contiene funzioni riutilizzabili per lettura e salvataggio dei file, creazione delle cartelle, normalizzazione delle stringhe, conversione degli importi, gestione delle date e controlli sulle colonne.

`scripts/src` contiene il codice operativo del progetto. Ogni file ha una responsabilità specifica.

`notebooks` contiene notebook numerati per controlli, analisi, focus territoriali e grafici finali. I notebook richiamano le funzioni presenti in `scripts`.

`output/data` contiene dati scaricati, puliti, trasformati e pronti per l'analisi.

`output/charts` contiene grafici, immagini e visualizzazioni prodotte dal codice.

## Fonti dati

La fonte operativa iniziale è OpenPNRR.

I file configurati sono missioni, componenti, misure, scadenze, organizzazioni, territori, progetti, localizzazioni dei progetti, pagamenti dei progetti e gare associate a CIG PNRR.

I link sono definiti in `scripts/config.py` dentro la costante `OPENPNRR_SOURCES`.

Il progetto è predisposto per integrare anche Italia Domani, ANAC, OpenCUP e ISTAT.

## Installazione

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Su Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

## Esecuzione

Esegui tutta la pipeline dalla radice del repository.

```bash
python scripts/src/run_pnrr_pipeline.py
```

Puoi eseguire le fasi separatamente.

```bash
python scripts/src/download_pnrr_data.py
python scripts/src/clean_pnrr_projects.py
python scripts/src/build_pnrr_indicators.py
python scripts/src/make_pnrr_charts.py
```

La data dello snapshot è definita in `scripts/config.py`. Per impostazione predefinita usa la data corrente. Per rendere ripetibile una lavorazione, modifica `DEFAULT_SNAPSHOT` oppure passa una data chiamando le funzioni dai notebook.

## Output prodotti

I dati vengono salvati in `output/data`.

```text
output/data/raw/<snapshot>/
  file originali scaricati dalle fonti
  manifest.json

output/data/clean/<snapshot>/
  projects.csv
  payments.csv
  locations.csv
  territories.csv

output/data/indicators/<snapshot>/
  projects_payments.csv
  territory_projects.csv
  national_summary.csv
  regional_summary.csv
  province_summary.csv
  metropolitan_city_summary.csv
  province_and_metropolitan_city_summary.csv
  municipal_summary.csv
```

I grafici vengono salvati in `output/charts/<snapshot>/`.

La prima versione produce `top_regions_by_pnrr_funding.png`, `top_regions_by_payment_progress.png` e `top_municipalities_by_pnrr_funding.png`.

## Definizioni principali

`finanziamento_pnrr` indica l'importo finanziato con risorse PNRR quando la colonna è disponibile nella fonte.

`pagamento_pnrr` indica i pagamenti PNRR cumulati registrati nel dataset dei pagamenti.

`payment_progress_pnrr` è il rapporto tra `pagamento_pnrr` e `finanziamento_pnrr`.

`payment_progress_total` è il rapporto tra `pagamento_tot` e `finanziamento_totale`.

`project_key` è la chiave tecnica usata per collegare progetti, pagamenti e localizzazioni. La pipeline la costruisce usando CUP e codice locale progetto. Quando queste informazioni mancano, usa l'identificativo progetto disponibile nella fonte.

`territory_id` è il codice territoriale normalizzato usato negli aggregati.

## Metodologia

La pipeline scarica i file configurati e salva una copia originale in una cartella snapshot. Il nome della cartella identifica la data della lavorazione.

Poi normalizza i nomi delle colonne. La normalizzazione trasforma i nomi in minuscolo, rimuove accenti e caratteri speciali e usa lo snake case.

Gli importi vengono convertiti in numeri gestendo sia il formato italiano sia il formato anglosassone.

I progetti vengono collegati ai pagamenti e alle localizzazioni attraverso `project_key`.

Gli aggregati territoriali sono costruiti separando i livelli pubblicati nella fonte: `R` regioni, `P` province, `CM` città metropolitane, `C` comuni.

I progetti multi-localizzati sono trattati con riparto uniforme entro ciascun livello territoriale. Se un progetto è collegato a tre comuni, ogni comune riceve un terzo dell'importo negli aggregati comunali. Questa scelta evita doppi conteggi quando si sommano i territori dello stesso livello.

La stessa regola viene applicata ai finanziamenti e ai pagamenti. Le colonne allocate hanno suffisso `_allocated`.

Gli indicatori di avanzamento sono rapporti tra pagamenti e finanziamenti. Quando il denominatore è nullo o mancante, il risultato viene lasciato vuoto.

## Assunzioni

Il dataset dei pagamenti viene interpretato come stock cumulato alla data di aggiornamento pubblicata dalla fonte.

La data dello snapshot locale indica quando i dati sono stati scaricati. Non coincide necessariamente con la data amministrativa del pagamento.

Il riparto uniforme dei progetti multi-localizzati è una convenzione analitica. Non stima il riparto amministrativo effettivo della spesa quando la fonte non lo pubblica.

## Limitazioni

Il repository non ricostruisce ogni euro a livello di fattura, SAL o mandato di pagamento.

La granularità temporale dipende dagli snapshot salvati. Per costruire una serie storica bisogna eseguire periodicamente il download e conservare ogni snapshot.

Alcuni progetti possono non avere pagamenti associati, localizzazioni complete o codici territoriali utilizzabili. Questi casi devono essere verificati nei controlli di qualità.

I confronti pro capite richiedono una fonte demografica aggiuntiva. La prima versione non integra automaticamente la popolazione ISTAT.

I dati su gare e contratti richiedono controlli specifici su CIG, stazioni appaltanti, aggiudicatari e importi. La prima versione prepara la fonte ma non costruisce ancora indicatori di rischio sugli appalti.

## Guida all'interpretazione

`national_summary.csv` descrive il quadro nazionale senza duplicare i progetti territorializzati.

`regional_summary.csv` permette di confrontare regioni per finanziamento PNRR allocato, pagamenti allocati e avanzamento finanziario.

`municipal_summary.csv` permette analisi comunali. Gli importi comunali sono costruiti con riparto uniforme dei progetti multi-localizzati.

Un valore alto di `payment_progress_pnrr_allocated` indica che, rispetto al finanziamento PNRR allocato al territorio, una quota maggiore risulta pagata nel dataset disponibile.

Un valore basso non indica automaticamente ritardo amministrativo. Può dipendere da natura dell'intervento, calendario dei lavori, regole di rendicontazione, aggiornamento della fonte o localizzazione del progetto.

I grafici servono come sintesi visiva. Le decisioni analitiche vanno sempre verificate sulle tabelle in `output/data`.
