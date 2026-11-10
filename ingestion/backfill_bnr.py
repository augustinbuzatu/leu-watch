"""Load the BNR exchange-rate history from the yearly archives into raw.bnr_rates.

Usage:
    uv run python -m ingestion.backfill_bnr                      # 2005 to this year
    uv run python -m ingestion.backfill_bnr --from-year 2017 --to-year 2017

Each year is committed as soon as it is loaded, so a failure in one year keeps
the years before it. Re-running is safe: existing rows are updated, not duplicated.
"""

import argparse
from datetime import date

from ingestion.config import load_database_settings
from ingestion.extract_bnr import (
    FIRST_ARCHIVE_YEAR,
    fetch_rates,
    keep_selected_currencies,
    yearly_archive_url,
)
from ingestion.load import connect, create_bnr_rates_table, upsert_bnr_rates


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-year", type=int, default=FIRST_ARCHIVE_YEAR)
    parser.add_argument("--to-year", type=int, default=date.today().year)
    args = parser.parse_args(argv)

    settings = load_database_settings()
    with connect(settings) as conn:
        create_bnr_rates_table(conn)
        conn.commit()

        for year in range(args.from_year, args.to_year + 1):
            rates = keep_selected_currencies(fetch_rates(yearly_archive_url(year)))
            upsert_bnr_rates(conn, rates)
            conn.commit()
            print(f"{year}: loaded {len(rates)} rates")


if __name__ == "__main__":
    main()
