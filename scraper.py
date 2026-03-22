"""Scraper module: fetches tenders from TED and EIB APIs."""

from datetime import datetime

import requests
from config import (
    TED_API_URL, CPV_CODES, TED_FIELDS, TEXT_KEYWORDS_IT,
    TARGET_COUNTRIES, EIB_PROCUREMENT_API, EIB_DETAIL_URL,
    WORLDBANK_API_URL, WORLDBANK_TARGET_COUNTRIES,
    ANAC_API_URL, ANAC_LEGAL_KEYWORDS,
    BAHRAIN_TENDERS_URL, BAHRAIN_DETAIL_URL,
    TUNISIA_TENDERS_URL,
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


def fetch_worldbank_tenders() -> list[dict]:
    """
    Fetch consulting services tenders from the World Bank procurement API.
    Filters by legal keywords and target countries.
    """
    all_tenders = []
    notice_types = [
        "Request for Expression of Interest",
        "Invitation for Bids",
    ]

    for notice_type in notice_types:
        offset = 0
        while offset < 500:  # Safety limit: max 500 per notice type
            params = {
                "format": "json",
                "rows": 50,
                "os": offset,
                "notice_type_exact": notice_type,
                "procurement_group_exact": "CS",
                "qterm": "legal services",
                "srce": "both",
            }
            try:
                resp = requests.get(WORLDBANK_API_URL, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                print(f"  [!] World Bank API error: {e}")
                break

            notices = data.get("procnotices", [])
            if not notices:
                break

            for notice in notices:
                tender = _normalize_worldbank_notice(notice)
                if tender:
                    all_tenders.append(tender)

            total = int(data.get("total", 0))
            offset += 50
            if offset >= total:
                break

    print(f"  Fetched {len(all_tenders)} tenders from World Bank API.")
    return all_tenders


def _normalize_worldbank_notice(notice: dict) -> dict | None:
    """Convert a World Bank notice to our standard format, filtering by target country."""
    notice_id = notice.get("id", "")
    if not notice_id:
        return None

    country_name = notice.get("project_ctry_name", "") or ""
    # Filter: only keep tenders in our target countries
    if not any(tc.lower() in country_name.lower() for tc in WORLDBANK_TARGET_COUNTRIES):
        return None

    title = notice.get("bid_description", "") or notice.get("project_name", "") or "N/A"
    buyer = notice.get("contact_organization", "") or "World Bank"

    # Parse publication date — format "19-Mar-2026"
    pub_date = ""
    raw_date = notice.get("noticedate", "")
    if raw_date:
        try:
            pub_date = datetime.strptime(raw_date, "%d-%b-%Y").strftime("%Y-%m-%d")
        except ValueError:
            pub_date = raw_date

    # Parse deadline
    deadline = ""
    raw_deadline = notice.get("submission_deadline_date", "") or ""
    if raw_deadline:
        try:
            deadline = datetime.fromisoformat(
                raw_deadline.replace("Z", "+00:00")
            ).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            deadline = raw_deadline[:10]

    link = f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}"

    return {
        "id": f"WB-{notice_id}",
        "title": title,
        "buyer": buyer,
        "country": country_name,
        "deadline": deadline,
        "cpv": "",
        "publication_date": pub_date,
        "link": link,
        "source": "World Bank",
    }


def fetch_anac_tenders() -> list[dict]:
    """
    Fetch Italian legal services tenders from ANAC open data API.
    Queries for each legal keyword and deduplicates by CIG code.
    """
    all_tenders: dict[str, dict] = {}  # keyed by CIG to deduplicate

    for keyword in ANAC_LEGAL_KEYWORDS:
        params = {"oggetto": keyword, "page": 1, "per_page": 100}
        try:
            resp = requests.get(ANAC_API_URL, params=params, timeout=30)
            if resp.status_code == 404:
                break  # Endpoint not available
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"  [!] ANAC API error ({keyword}): {e}")
            continue

        results = data if isinstance(data, list) else data.get("results", data.get("data", []))
        for item in results:
            tender = _normalize_anac_item(item)
            if tender and tender["id"] not in all_tenders:
                all_tenders[tender["id"]] = tender

    result = list(all_tenders.values())
    print(f"  Fetched {len(result)} tenders from ANAC API.")
    return result


def _normalize_anac_item(item: dict) -> dict | None:
    """Convert an ANAC OCDS item to our standard format."""
    # ANAC OCDS format uses 'ocid' or 'cig' as identifier
    cig = item.get("cig") or item.get("ocid", "")
    if not cig:
        return None

    # OCDS tender object may be nested
    tender_obj = item.get("tender", item)
    title = tender_obj.get("title") or item.get("oggetto", "") or "N/A"
    buyer = ""
    parties = item.get("parties", [])
    for party in parties:
        if "buyer" in party.get("roles", []):
            buyer = party.get("name", "")
            break
    if not buyer:
        buyer = item.get("stazione_appaltante", "Pubblica Amministrazione italiana")

    pub_date = item.get("date", "") or item.get("data_pubblicazione", "")
    if pub_date:
        pub_date = pub_date[:10]

    deadline = ""
    tender_period = tender_obj.get("tenderPeriod", {})
    if tender_period:
        deadline = (tender_period.get("endDate") or "")[:10]

    ocid = item.get("ocid", cig)
    link = f"https://dati.anticorruzione.it/superset/dashboard/appalti/?cig={cig}"

    return {
        "id": f"ANAC-{cig}",
        "title": title,
        "buyer": buyer,
        "country": "Italy",
        "deadline": deadline,
        "cpv": "",
        "publication_date": pub_date,
        "link": link,
        "source": "ANAC",
    }


def fetch_bahrain_tenders() -> list[dict]:
    """
    Fetch live tenders from Bahrain Tender Board via undocumented public AJAX endpoint.
    No authentication required.
    """
    all_tenders = []
    for view in ("NewTenders", "ToBeOpenedTenders"):
        try:
            resp = requests.get(
                BAHRAIN_TENDERS_URL,
                params={"viewFlag": view},
                headers={"X-Requested-With": "XMLHttpRequest"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"  [!] Bahrain Tender Board error ({view}): {e}")
            continue

        records = []
        if isinstance(data, list) and data:
            records = data[0].get("NewTndRecord", data[0].get("TndRecord", []))
        elif isinstance(data, dict):
            records = data.get("NewTndRecord", data.get("TndRecord", []))

        for item in records:
            tender = _normalize_bahrain_item(item)
            if tender:
                all_tenders.append(tender)

    print(f"  Fetched {len(all_tenders)} tenders from Bahrain Tender Board.")
    return all_tenders


def _normalize_bahrain_item(item: dict) -> dict | None:
    ref = item.get("TndRefNo", "") or item.get("tendertxnno", "")
    if not ref:
        return None

    title = item.get("tendertitle", "") or item.get("TndDesc", "") or "N/A"
    buyer = item.get("DivName", "Bahrain Government")

    deadline = ""
    raw_deadline = item.get("bidClosingOn", "") or ""
    if raw_deadline:
        # Format: "DD/MM/YYYY HH:MM AM/PM" or ISO
        try:
            deadline = datetime.strptime(raw_deadline[:10], "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            deadline = raw_deadline[:10]

    pub_date = ""
    raw_pub = item.get("bidOpeningOn", "") or ""
    if raw_pub:
        try:
            pub_date = datetime.strptime(raw_pub[:10], "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            pub_date = raw_pub[:10]

    link = BAHRAIN_DETAIL_URL.format(ref=ref)

    return {
        "id": f"BHR-{ref}",
        "title": title,
        "buyer": buyer,
        "country": "Bahrain",
        "deadline": deadline,
        "cpv": "",
        "publication_date": pub_date,
        "link": link,
        "source": "Bahrain Tender Board",
    }


def fetch_tunisia_tenders() -> list[dict]:
    """
    Fetch tenders from Tunisia's HAICOP portal (marchespublics.gov.tn).
    Uses the DataTable AJAX JSON endpoint — no authentication required.
    """
    all_tenders = []
    start = 0
    page_size = 100

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.marchespublics.gov.tn/fr/appels-doffres",
    }

    while True:
        data = {
            "draw": str(start // page_size + 1),
            "start": str(start),
            "length": str(page_size),
            "search[value]": "",
            "search[regex]": "false",
        }
        try:
            resp = requests.post(
                TUNISIA_TENDERS_URL, data=data, headers=headers, timeout=30
            )
            resp.raise_for_status()
            result = resp.json()
        except requests.RequestException as e:
            print(f"  [!] Tunisia HAICOP error: {e}")
            break

        records = result.get("data", [])
        if not records:
            break

        for item in records:
            tender = _normalize_tunisia_item(item)
            if tender:
                all_tenders.append(tender)

        total = result.get("recordsTotal", 0)
        start += page_size
        if start >= min(total, 500):  # safety cap at 500
            break

    print(f"  Fetched {len(all_tenders)} tenders from Tunisia HAICOP.")
    return all_tenders


def _normalize_tunisia_item(item: dict) -> dict | None:
    tid = item.get("id", "")
    if not tid:
        return None

    title = item.get("title_fr", "") or item.get("title_ar", "") or "N/A"
    buyer_obj = item.get("organization", {}) or {}
    buyer = buyer_obj.get("name_fr", "") or buyer_obj.get("name_ar", "") or "N/A"

    deadline = (item.get("tenderPeriod_endDate", "") or "")[:10]
    pub_date = (item.get("publication_date", "") or "")[:10]

    link = f"https://www.marchespublics.gov.tn/fr/appels-doffres/{tid}"

    return {
        "id": f"TUN-{tid}",
        "title": title,
        "buyer": buyer,
        "country": "Tunisia",
        "deadline": deadline,
        "cpv": "",
        "publication_date": pub_date,
        "link": link,
        "source": "Tunisia HAICOP",
    }


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
