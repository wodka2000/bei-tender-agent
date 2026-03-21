# BEI Tender Agent

Monitors legal and consulting tenders from the [TED (Tenders Electronic Daily)](https://ted.europa.eu) API, filtering for Italy, EU institutions and MENA countries.

## What it does

1. Queries the TED API for tenders with CPV codes related to legal services (791xxxxx) and management consultancy (794xxxxx)
2. Filters results by country (Italy, Belgium, Luxembourg, Saudi Arabia, Jordan, Iraq, Syria, Egypt, Oman, UAE, etc.)
3. Compares with previously seen tenders (`data/seen_tenders.json`)
4. Writes a Markdown report of **only new tenders** to `output/report.md`

No emails, no scheduling — just run it whenever you want an update.

A local web app is also available to browse all tracked tenders in a table.

## Installation

```bash
pip install -r requirements.txt
```

Dependencies: `requests` and `flask`.

## Usage

### CLI (batch mode)

```bash
python main.py
```

Output:
- `output/report.md` — human-readable report of new tenders
- `data/seen_tenders.json` — persistent tracker (auto-created)

### Web app

```bash
python app.py
```

At startup the app refreshes tenders from the TED API, then serves a local web interface at **http://127.0.0.1:5000** where you can browse all tracked tenders in a sortable table.

#### Filtri disponibili

La pagina principale include un form con filtri combinabili (logica AND):

| Filtro | Descrizione |
|--------|-------------|
| **Paese** | Select con tutti i TARGET_COUNTRIES da `config.py` (+ "Tutti i paesi") |
| **Buyer** | Campo di testo libero, ricerca case-insensitive (contiene) |
| **Tipo CPV** | Checkbox: "Servizi legali" (791xx) e/o "Consulenza / management" (794xx) |
| **Data pubblicazione** | Due campi data (dal / al) per filtrare per intervallo |
| **Solo BEI** | Checkbox che limita ai buyer corrispondenti a TARGET_BUYERS |

I risultati sono ordinati per data di pubblicazione decrescente. I filtri restano precompilati dopo il submit.

## Project structure

```
├── main.py           # CLI entry point
├── app.py            # Flask web app
├── scraper.py        # TED API client
├── filters.py        # Country and relevance filters
├── storage.py        # JSON persistence and report generation
├── config.py         # CPV codes, countries, keywords, paths
├── requirements.txt
├── templates/
│   └── index.html          # Web UI (Bootstrap table)
├── data/
│   └── seen_tenders.json   (auto-generated)
└── output/
    └── report.md           (auto-generated)
```

## Configuration

Edit `config.py` to:

- Add/remove **CPV codes** (e.g. add `79500000` for support services)
- Add/remove **target countries** (ISO 3166-1 alpha-3 codes)
- Add/remove **keyword filters** for title matching
- Add **target buyers** to always include (e.g. `"World Bank"`)

## Adding new sources

The scraper is designed to be extended. To add a new institution:

1. Create a new function in `scraper.py` (e.g. `fetch_tenders_from_worldbank()`)
2. Return a list of dicts with keys: `id`, `title`, `buyer`, `country`, `deadline`, `cpv`, `link`, `source`
3. Call it from `main.py` and merge results with the existing list

## API

The TED API is free and requires no authentication. Documentation: https://docs.ted.europa.eu/api/latest/index.html
