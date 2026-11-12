"""Download the National Bank of Romania (BNR) reference exchange rates and parse them.

The BNR publishes the rates as XML: one <Cube date="..."> per banking day, with one
<Rate currency="..." multiplier="..."> per currency, in lei for 1 unit of the currency
(or for 100 units when multiplier="100").
"""

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

import requests

YEARLY_ARCHIVE_URL = "https://curs.bnr.ro/files/xml/years/nbrfxrates{year}.xml"
FIRST_ARCHIVE_YEAR = 2005

# Main currencies plus regional peers (decision log, PR 2).
CURRENCIES = ("EUR", "USD", "GBP", "CHF", "HUF", "PLN", "CZK")

# BNR writes "-" when a currency has no rate on that day (e.g. BGN, RUB, SKK in 2007).
# Such entries carry no value, so they are skipped. None of CURRENCIES has one (2005-2026).
NO_RATE = "-"

MAX_ATTEMPTS = 5
FIRST_RETRY_DELAY_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 30
HEADERS = {"User-Agent": "leu-watch (+https://github.com/augustinbuzatu/leu-watch)"}


class InvalidBnrResponse(Exception):
    """The response is not a BNR exchange-rate document, e.g. an HTML error page."""


@dataclass(frozen=True)
class BnrRate:
    rate_date: date
    currency: str
    rate: Decimal
    multiplier: int | None  # None when the XML has no multiplier attribute


def yearly_archive_url(year: int) -> str:
    return YEARLY_ARCHIVE_URL.format(year=year)


def _local_name(tag: str) -> str:
    """Drop the XML namespace: "{https://www.bnr.ro/xsd}Cube" -> "Cube".

    Matching on the local name keeps the parser working across the namespace
    change from http:// (older files) to https:// (2026 files).
    """
    return tag.rsplit("}", 1)[-1]


def parse_rates(xml_document: bytes | str) -> list[BnrRate]:
    """Turn a BNR XML document into one BnrRate per day and currency with a rate."""
    try:
        root = ET.fromstring(xml_document)
    except ET.ParseError as error:
        raise InvalidBnrResponse(f"response is not valid XML: {error}") from error

    # The BNR error page is valid XHTML, so parsing alone does not prove anything.
    if _local_name(root.tag) != "DataSet":
        raise InvalidBnrResponse(f"expected a BNR <DataSet>, got <{_local_name(root.tag)}>")

    rates = []
    for cube in root.iter():
        if _local_name(cube.tag) != "Cube":
            continue
        rate_date = date.fromisoformat(cube.attrib["date"])
        for element in cube:
            if _local_name(element.tag) != "Rate":
                continue
            currency = element.attrib["currency"]
            text = (element.text or "").strip()
            if text == NO_RATE:
                continue
            try:
                rate = Decimal(text)
            except InvalidOperation:
                raise ValueError(
                    f"unexpected rate {text!r} for {currency} on {rate_date}"
                ) from None
            multiplier = element.get("multiplier")
            rates.append(
                BnrRate(
                    rate_date=rate_date,
                    currency=currency,
                    rate=rate,
                    multiplier=int(multiplier) if multiplier else None,
                )
            )
    return rates


def keep_selected_currencies(
    rates: list[BnrRate], currencies: tuple[str, ...] = CURRENCIES
) -> list[BnrRate]:
    return [rate for rate in rates if rate.currency in currencies]


def fetch_rates(url: str) -> list[BnrRate]:
    """Download and parse a BNR XML file, retrying when the server fails.

    The BNR server often answers with an HTML error page and HTTP 200, so an
    attempt only succeeds once the response parses as a BNR document.
    Waits 5, 10, 20 and 40 seconds between the 5 attempts.
    """
    delay = FIRST_RETRY_DELAY_SECONDS
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return parse_rates(response.content)
        except (requests.RequestException, InvalidBnrResponse) as error:
            if attempt == MAX_ATTEMPTS:
                raise
            print(
                f"Attempt {attempt}/{MAX_ATTEMPTS} failed for {url}: {error}. "
                f"Retrying in {delay} s."
            )
            time.sleep(delay)
            delay *= 2
