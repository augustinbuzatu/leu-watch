# Leu Watch: project plan

An automated data pipeline that loads the National Bank of Romania (BNR) exchange rates (daily) and
Eurostat inflation data (monthly) into PostgreSQL, models them with dbt, and serves a Power BI
dashboard with a simple inflation forecast.

Guiding rule: **use the simplest tool that does the job.** More complex options are listed as
"Level 2" and are added only after the first version works end to end.

## Architecture

```text
Public sources (BNR XML, Eurostat API)
        │
        ▼  ── GitHub Actions: runs automatically once a day ─────────────────
1. Ingestion · Python          downloads the data and loads it unchanged
        ▼
2. raw · PostgreSQL            faithful copy of the source data
        ▼
3. staging · dbt               correct types, clear names, no duplicates
        ▼                      (dbt tests + pytest: the run stops if they fail)
4. marts · dbt                 facts and dimensions (star schema)
        │──► 5. Forecast · Python   writes predictions back to the database
        ▼  ──────────────────────────────────────────────────────────────────
Dashboard · Power BI           reads the mart tables
```

## Data sources (no API key needed)

- **BNR exchange rates (XML):**
  - current: `https://curs.bnr.ro/nbrfxrates.xml`
  - last 10 banking days: `https://curs.bnr.ro/nbrfxrates10days.xml`
  - yearly archive, from 2005: `https://curs.bnr.ro/files/xml/years/nbrfxrates<YYYY>.xml`
  - Verified in PR 2: the yearly archives (2005 onwards) and the current file work on
    `curs.bnr.ro`. The server often returns an HTML error page with HTTP 200, and the XML
    namespace changed from `http://` to `https://` in 2026. The 10-day file is verified in PR 8.
- **Eurostat monthly inflation (HICP) for Romania and the EU:**
  - API: `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/<dataset>?...`
  - JSON-stat response, no authentication.
  - The dataset for the HICP monthly annual rate is probably `prc_hicp_manr`; verify in PR 5.

## Stack

| Layer | Tool | Why | Level 2 |
| --- | --- | --- | --- |
| Ingestion | Python (`requests`, `pandas`) | One short script per source, easy to read and test; simple retries, since the BNR server often fails | Structured logging |
| Storage | PostgreSQL: Docker locally, Supabase live | Familiar SQL, free, same concepts as a data warehouse | Snowflake / BigQuery |
| Transformation | dbt Core (`dbt-postgres`) | SQL transformations, run in order, tested and documented | Incremental models, snapshots |
| Data quality | dbt tests + `pytest` | Catch missing, duplicate or impossible values before the dashboard | Freshness alerts |
| Orchestration | GitHub Actions, daily schedule | Free, no server to maintain, fits one daily pipeline | Airflow / Prefect |
| Forecasting | `statsmodels` + naive baseline | Econometrics, evaluated honestly | More models, backtesting |
| Visualization | Power BI Desktop | Most requested BI tool in job ads; free on Windows | Streamlit for a live link |
| Infrastructure | Docker Compose, `.env`, GitHub Secrets | One-command setup; no credentials in code | Azure deployment |

Supabase free plan: 500 MB per project; free projects pause after one week of inactivity.

## Architecture decisions

1. **ELT, not ETL:** data is loaded unchanged, then transformed in SQL. A wrong transformation is
   fixed and re-run without downloading everything again.
2. **Three layers, raw → staging → marts:** each layer has a single responsibility.
3. **Star schema in marts:** a fact table (indicator values by date) and dimensions (calendar,
   currency, country). The standard BI model, and the one Power BI works best with.
4. **Idempotent runs:** running the pipeline twice creates no duplicates (upsert on a natural key,
   for example date + currency).
5. **Tests are a gate:** if a test fails, the run stops. Yesterday's data beats wrong data today.
6. **GitHub Actions instead of Airflow:** one linear daily pipeline doesn't justify an
   orchestration server.
7. **Honest forecast evaluation:** the model is compared with a naive baseline on the most recent
   periods, never on a random split, which would let a time-series model see the future. Metric: MAE.
8. **No credentials in code:** `.env` locally (git-ignored), GitHub Secrets in Actions.
9. **Local first, live later:** PostgreSQL in Docker, then the same schema on Supabase.

Modeling problem to explain: exchange rates are daily, inflation is monthly. Rates are aggregated
to a monthly value before they are compared with inflation.

## Repository structure

```text
leu-watch/
├── ingestion/            # Python: extract_bnr.py, extract_eurostat.py, load.py, tests/
├── dbt/
│   └── models/
│       ├── staging/      # stg_bnr_rates.sql, stg_eurostat_hicp.sql
│       └── marts/        # fct_..., dim_... + .yml files with tests and descriptions
├── forecasting/          # forecast.py: baseline + model, writes predictions to the database
├── dashboard/            # report.pbix + screenshots/
├── docs/                 # plan.md (this plan), decisions.md (decision log)
├── .github/workflows/    # pipeline.yml (daily), ci.yml (on pull requests)
├── docker-compose.yml    # local PostgreSQL
├── .env.example          # required variables, no real values
└── README.md             # diagram, decisions, how to run, screenshots
```

## Roadmap: 14 pull requests

Each PR makes one change that can be reviewed in a few minutes. The target pace is one PR a day,
but order matters more than the calendar. Each PR has one **decision** I make before the code is
written; the choice and its reason go into `docs/decisions.md`.

**Foundation**

- [x] **PR 1 · Project skeleton:** folder structure, `.gitignore`, `.env.example`, PostgreSQL in
      Docker Compose, Python dependencies, minimal README.
      *Decision:* how Python dependencies are managed (`pip` + `requirements.txt` or `uv`).
- [x] **PR 2 · BNR rates into `raw`:** downloads the history from the yearly archives and loads it
      with an upsert; running it twice creates no duplicates.
      *Decision:* which currencies to keep and how far back the history goes.
- [x] **PR 3 · Tests and CI:** `pytest` tests for the BNR XML parser and a GitHub Actions workflow
      that runs them on every pull request. (The parser tests were written with the parser, in PR 2.)
      *Decision:* what CI checks (tests only, or formatting and linting too).

**Transformations**

- [ ] **PR 4 · dbt and BNR staging:** dbt setup and the `stg_bnr_rates` model with tests.
      *Decision:* how to handle currencies quoted per 100 units (the XML `multiplier` attribute,
      to be verified) and the naming conventions.
- [ ] **PR 5 · Eurostat inflation into `raw`:** the Eurostat API script, with tests.
      *Decision:* which countries to compare with Romania (EU average, neighbours) and from which year.
- [ ] **PR 6 · Eurostat staging:** the `stg_eurostat_hicp` model, with periods like `2024M01`
      converted to dates.
      *Decision:* how months are represented (first day of the month or a year-month key).
- [ ] **PR 7 · Marts (star schema):** dimensions (calendar, currency, country) and fact tables
      (daily rates, monthly indicators), with tests.
      *Decision:* table grain and how daily rates are aggregated monthly (monthly average or
      end-of-month value).

**Automation**

- [ ] **PR 8 · Daily mode:** the daily run reads only the 10-day file; one script runs the whole
      pipeline locally, end to end.
      *Decision:* what happens on weekends and holidays, when BNR publishes nothing.
- [ ] **PR 9 · Supabase and scheduled runs:** database moved to Supabase, the daily workflow in
      GitHub Actions, credentials in GitHub Secrets.
      *Decision:* the run time and how I am notified when something fails.

**Dashboard**

- [ ] **PR 10 · Power BI:** report connected to the marts, 3–4 charts, screenshots in
      `dashboard/screenshots/`. Built on my Windows machine, since Power BI Desktop runs only there.
      *Decision:* which question each chart answers.

**Forecast**

- [ ] **PR 11 · Baseline and evaluation:** the naive forecast and an evaluation on the most recent
      months (MAE).
      *Decision:* forecast horizon and test period.
- [ ] **PR 12 · statsmodels model:** the model compared with the baseline; predictions written to
      the database.
      *Decision:* which model, and what to do if it doesn't beat the baseline.
- [ ] **PR 13 · Forecast in the pipeline and dashboard:** the forecast runs automatically and the
      dashboard gets a forecast page.
      *Decision:* how often the model is retrained (daily or with each new month of inflation data).

**Polish**

- [ ] **PR 14 · README and demo:** diagram, decisions in short, screenshots, run commands and a
      short demo video.
      *Decision:* what to highlight for a recruiter.

PR 9 (Supabase and secrets) and PR 10 (Power BI) will probably take longest. A PR that grows too
large is split in two; two PRs that turn out too small are merged.

## Operations

- The pipeline runs on its own; I step in only when an email says a test failed.
- Power BI Desktop doesn't refresh itself: open the report and press Refresh before updating
  screenshots or presenting it.
- GitHub disables scheduled workflows in a public repository after 60 days without activity;
  re-enable them with one click, or push a commit.
