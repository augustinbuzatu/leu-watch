"""Load data into the raw schema of PostgreSQL.

Loads are idempotent: rows are upserted on their natural key, so running the
same load twice leaves the table unchanged instead of creating duplicates.
"""

import psycopg

from ingestion.config import DatabaseSettings
from ingestion.extract_bnr import BnrRate

CREATE_RAW_SCHEMA_SQL = "CREATE SCHEMA IF NOT EXISTS raw"

CREATE_BNR_RATES_SQL = """
CREATE TABLE IF NOT EXISTS raw.bnr_rates (
    rate_date   date        NOT NULL,
    currency    text        NOT NULL,
    rate        numeric     NOT NULL,  -- exact decimal, e.g. 4.9749 stays 4.9749
    multiplier  integer,               -- NULL when the XML has no multiplier attribute
    loaded_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (rate_date, currency)
)
"""

# If BNR corrects a published rate, the new value replaces the old one.
UPSERT_BNR_RATE_SQL = """
INSERT INTO raw.bnr_rates (rate_date, currency, rate, multiplier)
VALUES (%s, %s, %s, %s)
ON CONFLICT (rate_date, currency) DO UPDATE
SET rate = EXCLUDED.rate,
    multiplier = EXCLUDED.multiplier,
    loaded_at = now()
"""


def connect(settings: DatabaseSettings) -> psycopg.Connection:
    return psycopg.connect(
        host=settings.host,
        port=settings.port,
        dbname=settings.dbname,
        user=settings.user,
        password=settings.password,
    )


def create_bnr_rates_table(conn: psycopg.Connection) -> None:
    conn.execute(CREATE_RAW_SCHEMA_SQL)
    conn.execute(CREATE_BNR_RATES_SQL)


def upsert_bnr_rates(conn: psycopg.Connection, rates: list[BnrRate]) -> None:
    """Insert or update the rates. The caller decides when to commit."""
    with conn.cursor() as cursor:
        cursor.executemany(
            UPSERT_BNR_RATE_SQL,
            [(r.rate_date, r.currency, r.rate, r.multiplier) for r in rates],
        )
