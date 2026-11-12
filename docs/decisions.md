# Decision log

Every architecture or design decision, with the reason behind it. The newest entry is at the end.

## 2026-11-04 · Before PR 1 · Project topic

- **Decision:** Leu Watch (BNR exchange rates and Eurostat inflation).
- **Options considered:** air quality in Bucharest, EU unemployment, tourism in Romania.
- **Reason:** it fits my background (financial data, economics) and poses a good modeling problem:
  linking daily data to monthly data.

## 2026-11-04 · Before PR 1 · Orchestration

- **Decision:** GitHub Actions on a daily schedule.
- **Options considered:** Airflow, Prefect.
- **Reason:** a single linear daily pipeline doesn't justify an orchestration server; Airflow stays
  a Level 2 option.

## 2026-11-04 · PR 1 · Python dependency management

- **Decision:** uv, with dependencies in `pyproject.toml` and exact versions in a committed
  `uv.lock`.
- **Options considered:** `pip` + `venv` + `requirements.txt`, Poetry.
- **Reason:** the lock file pins every package, including indirect ones such as `numpy`, so my
  machine, CI and the daily run use the same environment. One tool creates the virtual environment,
  installs the right Python and keeps dev dependencies (`pytest`) separate, while the commands stay
  as short as with pip (`uv sync`, `uv run pytest`). Poetry offers the same lock file but is slower
  and more complex to configure.

## 2026-11-04 · PR 1 · Python version

- **Decision:** Python 3.12, pinned in `.python-version`.
- **Options considered:** a newer version (3.13 or later).
- **Reason:** a stable version supported by every tool in the plan (pandas, dbt, statsmodels);
  newer versions bring nothing this project needs and add a risk that a package, dbt in
  particular, does not support them yet.

## 2026-11-04 · PR 1 · PostgreSQL version

- **Decision:** PostgreSQL 17 (the `postgres:17` Docker image).
- **Options considered:** PostgreSQL 16, PostgreSQL 18.
- **Reason:** Supabase uses PostgreSQL 17 for new projects, so the local database and the live one
  (PR 9) run the same major version.

## 2026-11-10 · PR 2 · Currencies and history

- **Decision:** seven currencies (EUR, USD, GBP and CHF, plus the regional peers HUF, PLN and
  CZK), with history from 2005, the first year of the BNR XML archive.
- **Options considered:** currencies: all 37 that BNR publishes (including gold, XAU, and the IMF
  SDR, XDR), or only EUR and USD; history: from 2015.
- **Reason:** a focused dataset: the currencies that matter most for Romania and the economies it is
  usually compared with. All seven are published since 2005, so each has the full history, which
  covers the 2008 crisis, the pandemic and the 2022 inflation wave and gives the forecast a long
  series. Trade-off: filtering in ingestion departs from "load unchanged"; adding a currency later
  means re-running the backfill, which is safe because loads are idempotent.

## 2026-11-10 · PR 2 · Download retries

- **Decision:** a simple retry in the script: up to 5 attempts, waiting 5, 10, 20 and 40 seconds.
  An attempt succeeds only if the response parses as a BNR document.
- **Options considered:** no retries (re-run by hand), the `tenacity` library.
- **Reason:** while testing, 11 of 22 yearly files came back as an HTML error page with HTTP 200.
  Without retries the backfill would need many manual re-runs and the daily run would fail often.
  It takes about 10 lines and no new dependency. This brings forward an item the plan had listed as
  Level 2.

## 2026-11-10 · PR 2 · Column types in raw

- **Decision:** typed columns in `raw.bnr_rates`: `date`, `text`, `numeric` and `integer`.
- **Options considered:** every column as text, exactly as in the XML, with casts in staging.
- **Reason:** the conversion is lossless (`numeric` keeps the exact decimals), a malformed value
  stops the load immediately, and staging stays simpler. Real transformations, such as applying
  the multiplier, still happen in dbt.

## 2026-11-10 · PR 2 · Loading details

- **Decision:** `psycopg` 3 as the PostgreSQL driver; the upsert updates the rate when a row
  already exists (`ON CONFLICT ... DO UPDATE`) and records `loaded_at`; `multiplier` stays NULL
  when the XML has no multiplier attribute.
- **Options considered:** `psycopg2`; `ON CONFLICT DO NOTHING`; storing 1 when the attribute is
  missing.
- **Reason:** `psycopg` 3 is the maintained version (`psycopg2` only gets maintenance fixes). If BNR
  corrects a published rate, raw takes the correction. NULL keeps raw a faithful copy of the source;
  how the multiplier is applied is decided in PR 4.
- **Found while loading:** BNR writes `-` when a currency has no rate on a day (BGN, RUB and SKK in
  2007, ten currencies in 2009). The parser skips these entries, since they carry no value; any
  other non-numeric value stops the load. None of the seven chosen currencies has a `-` between
  2005 and 2026, and each has a rate on every banking day.

## 2026-11-12 · PR 3 · CI checks

- **Decision:** CI runs the tests plus Ruff (linting and a formatting check) on every pull request
  and on every push to `main`.
- **Options considered:** tests only; tests, Ruff and type checking with mypy.
- **Reason:** Ruff is one fast tool that replaces flake8, black and isort and keeps the style
  consistent at almost no cost: the existing code passed the linter and needed one formatting
  change. Type checking adds configuration and false alarms that a codebase this small doesn't
  justify yet; it stays Level 2.

## 2026-11-12 · PR 3 · Database tests in CI

- **Decision:** CI starts a PostgreSQL 17 service container, so the integration tests run on every
  pull request. In CI (`CI=true`) a missing database fails these tests instead of skipping them.
- **Options considered:** let the integration tests skip in CI.
- **Reason:** "loading twice creates no duplicates" is the main guarantee of the ingestion, so it
  must be checked automatically. A skipped test would let a broken database setup show as green.
  The container's password is a throwaway value for a database that exists only during the job.

## 2026-11-12 · PR 3 · CI details

- **Decision:** `uv sync --locked`, so CI fails if `uv.lock` is out of date; GitHub Actions pinned
  to a commit SHA with the version in a comment (`actions/checkout` v7.0.1, `astral-sh/setup-uv`
  v10.3.3); Ruff with a line length of 100 and import sorting on top of the default rules.
- **Options considered:** `uv sync` without `--locked`; version tags such as `@v7`.
- **Reason:** a tag can be moved by whoever controls the action's repository (as in the 2025
  `tj-actions/changed-files` attack); a commit SHA cannot. `setup-uv` no longer publishes major
  tags, so it needs an exact version anyway. Automatic updates of the pins (Dependabot) stay Level 2.
