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
