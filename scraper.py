"""Scraper module: fetches tenders from TED and EIB APIs."""

from datetime import datetime

import requests
from config import (
    TED_API_URL, CPV_CODES, TED_FIELDS, TEXT_KEYWORDS_IT,
    TARGET_COUNTRIES, EIB_PROCUREMENT_API, EIB_DETAIL_URL,
)


def fetch_tenders_from_ted() -> list[dict]:
    """
    Query the TED (Tenders Electronic Daily) API for legal/consulting tenders.
    The TED API is free and requires no authentication.
    Returns a list of tender dicts with normalized fields.
    """
    all_tenders = []

    # Build query: (CPV codes OR Italian full-text keywords) AND target countries
    cpv_conditions = " OR ".join(
        f'classification-cpv = "{code}"' for code in CPV_CODES
    )
    ft_terms = " OR ".join(TEXT_KEYWORDS_IT)
    country_list = ", ".join(f'"{code}"' for code in TARGET_COUNTRIES)

    query = (
        f"(({cpv_conditions}) OR FT=({ft_terms}))"
        f" AND (buyer-country IN ({country_list}))"
    )

    page = 1
    max_pages = 10  # Safety limit

    while page <= max_pages:
        payload = {
            "query": query,
            "fields": TED_FIELDS,
            "limit": 100,
            "scope": "ALL",
            "paginationMode": "PAGE_NUMBER",
            "page": page,
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            resp = requests.post(
                TED_API_URL, json=payload, headers=headers, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"  [!] Error querying TED API (page {page}): {e}")
            break

        notices = data.get("notices", [])
        if not notices:
            break

        for notice in notices:
            tender = _normalize_ted_notice(notice)
            if tender:
                all_tenders.append(tender)

        total = data.get("totalNoticeCount", 0)
        fetched = page * 100
        if fetched >= total:
            break
        page += 1

    print(f"  Fetched {len(all_tenders)} tenders from TED API.")
    return all_tenders


def _normalize_ted_notice(notice: dict) -> dict | None:
    """Convert a TED notice into our standard tender format."""
    pub_number = notice.get("publication-number")
    if not pub_number:
        return None

    title = _extract_multilingual(notice.get("notice-title"))
    buyer = _extract_multilingual(notice.get("buyer-name")) or \
            _extract_multilingual(notice.get("organisation-name-buyer"))
    country_list = notice.get("buyer-country", []) or []
    perf_country = notice.get("place-of-performance-country-lot", []) or []
    country = ", ".join(country_list) if country_list else ", ".join(perf_country)

    deadline = _extract_first(notice.get("deadline-receipt-tender-date-lot")) or \
               _extract_first(notice.get("deadline-receipt-request")) or "N/A"

    cpv_codes = notice.get("classification-cpv", []) or []
    # Keep only relevant CPV codes (79xxxxx)
    relevant_cpv = [c for c in cpv_codes if str(c).startswith("791") or str(c).startswith("794")]
    cpv_str = ", ".join(relevant_cpv[:3]) if relevant_cpv else ", ".join(cpv_codes[:3])

    pub_date = _extract_first(notice.get("publication-date")) or "N/A"

    link_html = notice.get("links", {}).get("html", {})
    link = link_html.get("ITA") or link_html.get("ENG") or \
           next(iter(link_html.values()), f"https://ted.europa.eu/en/notice/-/detail/{pub_number}")

    return {
        "id": pub_number,
        "title": title,
        "buyer": buyer or "N/A",
        "country": country or "N/A",
        "deadline": deadline,
        "cpv": cpv_str,
        "publication_date": pub_date,
        "link": link,
        "source": "TED",
    }


def fetch_eib_tenders() -> list[dict]:
    """
    Fetch procurement calls directly from the EIB website API.
    Returns calls for tenders and technical assistance operations
    in the same dict format used for TED results.
    """
    all_tenders = []

    # Fetch both EIB's own calls and TA operations (ongoing + recently closed)
    for status in ("ongoing",):
        params = {
            "sortColumn": "id",
            "sortDir": "desc",
            "pageNumber": 0,
            "itemPerPage": 100,
            "pageable": "true",
            "language": "EN",
            "defaultLanguage": "EN",
            "statuses": status,
        }

        try:
            resp = requests.get(
                EIB_PROCUREMENT_API, params=params, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"  [!] Error querying EIB API: {e}")
            return all_tenders

        for item in data.get("data", []):
            tender = _normalize_eib_item(item)
            if tender:
                all_tenders.append(tender)

    print(f"  Fetched {len(all_tenders)} tenders from EIB API.")
    return all_tenders


def _normalize_eib_item(item: dict) -> dict | None:
    """Convert an EIB procurement JSON item to our standard format."""
    url_slug = item.get("url", "")
    if not url_slug:
        return None

    title = item.get("title", "").strip()
    if not title:
        return None

    # additionalInformation: [status, type, reference, pub_date, deadline]
    info = item.get("additionalInformation") or []

    # Parse publication date from epoch ms or additionalInformation
    pub_date = ""
    if item.get("startDate"):
        pub_date = datetime.fromtimestamp(
            item["startDate"] / 1000
        ).strftime("%Y-%m-%d")
    elif len(info) >= 4 and info[3].strip():
        pub_date = _parse_eib_date(info[3])

    # Parse deadline from epoch ms or additionalInformation
    deadline = ""
    if item.get("endDate"):
        deadline = datetime.fromtimestamp(
            item["endDate"] / 1000
        ).strftime("%Y-%m-%d")
    elif len(info) >= 5 and info[4].strip():
        deadline = _parse_eib_date(info[4])

    # Build tender ID prefixed to avoid collisions with TED IDs
    tender_id = f"EIB-{url_slug}"

    link = EIB_DETAIL_URL.format(id=url_slug)

    return {
        "id": tender_id,
        "title": title,
        "buyer": "European Investment Bank (EIB)",
        "country": "LUX",
        "deadline": deadline,
        "cpv": "",
        "publication_date": pub_date,
        "link": link,
        "source": "EIB",
    }


def _parse_eib_date(raw: str) -> str:
    """Convert DD/MM/YYYY to YYYY-MM-DD."""
    raw = raw.strip()
    if not raw:
        return ""
    try:
        return datetime.strptime(raw, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _extract_multilingual(field) -> str:
    """Extract text from a multilingual dict, preferring English then Italian."""
    if not field:
        return ""
    if isinstance(field, str):
        return field
    if isinstance(field, dict):
        # Values can be strings or lists like {'ita': ['Name'], 'eng': 'Name'}
        for lang in ("ita", "eng", "fra"):
            val = field.get(lang)
            if val:
                if isinstance(val, list):
                    return ", ".join(str(v) for v in val)
                return str(val)
        # Fallback to first available
        first_val = next(iter(field.values()), "N/A")
        if isinstance(first_val, list):
            return ", ".join(str(v) for v in first_val)
        return str(first_val)
    if isinstance(field, list):
        return str(field[0]) if field else ""
    return str(field)


def _extract_first(field) -> str | None:
    """Extract first value from a field that may be a list or string."""
    if field is None:
        return None
    if isinstance(field, str):
        return field
    if isinstance(field, list):
        return str(field[0]) if field else None
    return str(field)
