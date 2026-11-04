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
