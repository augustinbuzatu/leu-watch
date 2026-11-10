"""Integration tests against the local PostgreSQL (docker compose up -d).

They are skipped when the database is not running. Every test runs inside a
transaction that is rolled back, so nothing is left in the database.
"""

from datetime import date
from decimal import Decimal

import psycopg
import pytest

from ingestion.config import load_database_settings
from ingestion.extract_bnr import BnrRate
from ingestion.load import connect, create_bnr_rates_table, upsert_bnr_rates

# XTS is the ISO 4217 code reserved for testing, so it never clashes with real rows.
TEST_RATES = [
    BnrRate(date(2025, 1, 3), "XTS", Decimal("4.9749"), None),
    BnrRate(date(2025, 1, 8), "XTS", Decimal("1.1994"), 100),
]


@pytest.fixture
def conn():
    try:
        connection = connect(load_database_settings())
    except (RuntimeError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL is not available: {error}")
    create_bnr_rates_table(connection)
    yield connection
    connection.rollback()
    connection.close()


def xts_rows(conn):
    return conn.execute(
        "SELECT rate_date, rate, multiplier FROM raw.bnr_rates "
        "WHERE currency = 'XTS' ORDER BY rate_date"
    ).fetchall()


def test_loading_twice_creates_no_duplicates(conn):
    upsert_bnr_rates(conn, TEST_RATES)
    upsert_bnr_rates(conn, TEST_RATES)

    assert xts_rows(conn) == [
        (date(2025, 1, 3), Decimal("4.9749"), None),
        (date(2025, 1, 8), Decimal("1.1994"), 100),
    ]


def test_a_corrected_rate_replaces_the_old_value(conn):
    upsert_bnr_rates(conn, TEST_RATES)
    corrected = BnrRate(date(2025, 1, 3), "XTS", Decimal("4.9750"), None)
    upsert_bnr_rates(conn, [corrected])

    assert xts_rows(conn)[0] == (date(2025, 1, 3), Decimal("4.9750"), None)
