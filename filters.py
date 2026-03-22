"""Filtering module: selects tenders relevant to our criteria."""

from config import TARGET_COUNTRIES, TARGET_BUYERS, LEGAL_KEYWORDS, CATEGORIES


def categorize_tender(tender: dict) -> str:
    """Assign a category based on CPV codes first, then title/buyer keywords."""
    cpv = tender.get("cpv", "") or tender.get("cpv_codes", "") or ""
    text = (
        (tender.get("title", "") or "") + " " + (tender.get("buyer", "") or "")
    ).lower()

    for category, rules in CATEGORIES.items():
        for prefix in rules["cpv_prefixes"]:
            if cpv and any(c.strip().startswith(prefix) for c in cpv.split(",")):
                return category
        for kw in rules["keywords"]:
            if kw.lower() in text:
                return category

    return "Altro"


def filter_tenders(tenders: list[dict]) -> list[dict]:
    """
    Filter tenders by:
    1. Country (Italy, EU institutions, MENA)
    2. Relevance (legal/consulting keywords OR matching buyer)
    Returns only tenders that pass all filters.
    """
    return [t for t in tenders if _matches_country(t) and _matches_relevance(t)]


def _matches_country(tender: dict) -> bool:
    """Check if tender country matches our target list."""
    country = tender.get("country", "").upper().strip()
    if not country or country == "N/A":
        return False

    for code in TARGET_COUNTRIES:
        if code in country:
            return True

    for name in TARGET_COUNTRIES.values():
        if name.upper() in country:
            return True

    return False


def _matches_relevance(tender: dict) -> bool:
    """Check if tender is about legal services (for lawyers / law firms)."""
    # CPV codes starting with 791 indicate legal services
    cpv = tender.get("cpv", "")
    if cpv and cpv.startswith("791"):
        return True

    # Check title and buyer for keywords
    text = f"{tender.get('title', '')} {tender.get('buyer', '')}".lower()
    for keyword in LEGAL_KEYWORDS:
        if keyword in text:
            return True

    # Check if buyer is one we're specifically tracking
    buyer = tender.get("buyer", "").lower()
    for target_buyer in TARGET_BUYERS:
        if target_buyer in buyer:
            return True

    return False
