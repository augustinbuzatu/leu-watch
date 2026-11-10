from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import requests

from ingestion import extract_bnr
from ingestion.extract_bnr import (
    BnrRate,
    InvalidBnrResponse,
    keep_selected_currencies,
    parse_rates,
)

FIXTURES = Path(__file__).parent / "fixtures"
RATES_2025 = (FIXTURES / "bnr_rates_2025_http_namespace.xml").read_bytes()
RATES_2026 = (FIXTURES / "bnr_rates_2026_https_namespace.xml").read_bytes()
ERROR_PAGE = (FIXTURES / "bnr_error_page.html").read_bytes()
NO_RATE_2007 = (FIXTURES / "bnr_rates_2007_no_rate.xml").read_bytes()


def test_parses_one_row_per_day_and_currency():
    rates = parse_rates(RATES_2025)

    assert len(rates) == 8  # 2 days x 4 currencies
    assert rates[0] == BnrRate(date(2025, 1, 3), "EUR", Decimal("4.9749"), None)
    assert rates[-1] == BnrRate(date(2025, 1, 8), "XAU", Decimal("411.4200"), None)


def test_keeps_the_multiplier_when_present():
    huf = [rate for rate in parse_rates(RATES_2025) if rate.currency == "HUF"]

    assert {rate.multiplier for rate in huf} == {100}


def test_parses_the_https_namespace_used_from_2026():
    rates = parse_rates(RATES_2026)

    assert rates == [
        BnrRate(date(2026, 1, 5), "EUR", Decimal("5.0905"), None),
        BnrRate(date(2026, 1, 5), "HUF", Decimal("1.3247"), 100),
    ]


def test_skips_currencies_marked_with_no_rate():
    rates = parse_rates(NO_RATE_2007)

    assert rates == [BnrRate(date(2007, 1, 3), "EUR", Decimal("3.3560"), None)]


def test_an_unexpected_rate_value_stops_the_parse():
    broken = RATES_2026.replace(b"5.0905", b"n/a")

    with pytest.raises(ValueError, match="unexpected rate 'n/a' for EUR on 2026-01-05"):
        parse_rates(broken)


def test_rejects_the_html_error_page():
    # The page is valid XHTML, so it parses as XML; it must still be rejected.
    with pytest.raises(InvalidBnrResponse, match="expected a BNR <DataSet>"):
        parse_rates(ERROR_PAGE)


def test_rejects_a_response_that_is_not_xml():
    with pytest.raises(InvalidBnrResponse, match="not valid XML"):
        parse_rates(b"Service unavailable")


def test_keeps_only_the_selected_currencies():
    rates = keep_selected_currencies(parse_rates(RATES_2025))

    assert {rate.currency for rate in rates} == {"EUR", "HUF", "USD"}  # XAU dropped


class FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


@pytest.fixture
def fake_server(monkeypatch):
    """Replace the network and the waiting: responses are served in order."""
    responses = []
    sleeps = []

    def fake_get(url, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(extract_bnr.requests, "get", fake_get)
    monkeypatch.setattr(extract_bnr.time, "sleep", sleeps.append)
    return responses, sleeps


def test_fetch_retries_after_error_responses(fake_server):
    responses, sleeps = fake_server
    responses += [
        FakeResponse(ERROR_PAGE),  # HTTP 200, but an HTML error page
        FakeResponse(b"", status_code=502),
        FakeResponse(RATES_2026),
    ]

    rates = extract_bnr.fetch_rates("https://example.test/rates.xml")

    assert len(rates) == 2
    assert sleeps == [5, 10]  # the wait doubles after each failure


def test_fetch_gives_up_after_the_last_attempt(fake_server):
    responses, sleeps = fake_server
    responses += [FakeResponse(ERROR_PAGE)] * extract_bnr.MAX_ATTEMPTS

    with pytest.raises(InvalidBnrResponse):
        extract_bnr.fetch_rates("https://example.test/rates.xml")

    assert sleeps == [5, 10, 20, 40]
