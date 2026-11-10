# Leu Watch

A daily data pipeline that tracks the Romanian leu (RON). It loads National Bank of Romania (BNR)
exchange rates and Eurostat inflation data into PostgreSQL, models them with dbt and serves a
Power BI dashboard with a simple inflation forecast.

Status: early development. See [docs/plan.md](docs/plan.md) for the roadmap and
[docs/decisions.md](docs/decisions.md) for the decision log.

## Requirements

- [Docker](https://docs.docker.com/get-docker/) with Docker Compose, for the local database
- [uv](https://docs.astral.sh/uv/getting-started/installation/), which installs Python 3.12 and
  every dependency at the exact versions in `uv.lock`

## Getting started

```bash
cp .env.example .env      # then set your own POSTGRES_PASSWORD
docker compose up -d      # starts PostgreSQL 17 on localhost:5432
uv sync                   # creates .venv and installs the dependencies
uv run pytest             # runs the tests
```

Stop the database with `docker compose down`. The data is kept in a Docker volume;
`docker compose down -v` deletes it.

The tests in `ingestion/tests/test_load.py` use the local database and are skipped when it is not
running.

## Loading the data

```bash
uv run python -m ingestion.backfill_bnr                                # BNR rates, 2005 to today
uv run python -m ingestion.backfill_bnr --from-year 2024 --to-year 2024 # one year only
```

The backfill downloads the BNR yearly archives and upserts them into `raw.bnr_rates`, so it can be
re-run safely. The BNR server often answers with an error page, so each download is retried up to
5 times.

## Repository structure

```text
ingestion/            Python scripts that download the source data and load it into raw
dbt/                  dbt project: staging and marts models (from PR 4)
forecasting/          inflation forecast (from PR 11)
dashboard/            Power BI report and screenshots (from PR 10)
docs/                 project plan and decision log
.github/workflows/    CI and the daily pipeline (from PR 3)
docker-compose.yml    local PostgreSQL
.env.example          required environment variables, without real values
```
