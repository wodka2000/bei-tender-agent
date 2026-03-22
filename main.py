"""
BEI Tender Agent - Main entry point.

Fetches tenders from multiple sources, filters, identifies new ones,
and sends Telegram notifications.
"""

from scraper import (
    fetch_tenders_from_ted, fetch_eib_tenders,
    fetch_worldbank_tenders, fetch_anac_tenders,
    fetch_bahrain_tenders, fetch_tunisia_tenders,
)
from filters import filter_tenders
from notifier import notify_new_tenders
from storage import (
    load_seen_tenders,
    save_seen_tenders,
    find_new_tenders,
    mark_as_seen,
    refresh_statuses,
    write_report,
    export_csv,
    normalize_deadline,
    compute_status,
)
from config import REPORT_PATH, CSV_PATH

ALL_SOURCES = ["TED", "EIB", "World Bank", "ANAC", "Bahrain", "Tunisia"]


def main(sources: list[str] | None = None, category_filter: str | None = None):
    """
    Run the tender check.
    sources: list of source names to query, or None for all.
    """
    if sources is None:
        sources = ALL_SOURCES

    print(f"=== BEI Tender Agent — fonti: {', '.join(sources)} ===\n")

    ted_tenders, eib_tenders, wb_tenders = [], [], []
    anac_tenders, bahrain_tenders, tunisia_tenders = [], [], []

    if "TED" in sources:
        print("Fetching TED...")
        ted_tenders = fetch_tenders_from_ted()
        print(f"  TED: {len(ted_tenders)}")

    if "EIB" in sources:
        print("Fetching EIB...")
        eib_tenders = fetch_eib_tenders()
        print(f"  EIB: {len(eib_tenders)}")

    if "World Bank" in sources:
        print("Fetching World Bank...")
        wb_tenders = fetch_worldbank_tenders()
        print(f"  World Bank: {len(wb_tenders)}")

    if "ANAC" in sources:
        print("Fetching ANAC...")
        anac_tenders = fetch_anac_tenders()
        print(f"  ANAC: {len(anac_tenders)}")

    if "Bahrain" in sources:
        print("Fetching Bahrain...")
        bahrain_tenders = fetch_bahrain_tenders()
        print(f"  Bahrain: {len(bahrain_tenders)}")

    if "Tunisia" in sources:
        print("Fetching Tunisia...")
        tunisia_tenders = fetch_tunisia_tenders()
        print(f"  Tunisia: {len(tunisia_tenders)}")

    relevant = (
        filter_tenders(ted_tenders)
        + eib_tenders + wb_tenders + anac_tenders
        + bahrain_tenders + tunisia_tenders
    )
    print(f"\nGare rilevanti: {len(relevant)}")

    seen = load_seen_tenders()
    new_tenders = find_new_tenders(relevant, seen)
    print(f"Nuove: {len(new_tenders)}")

    if new_tenders:
        seen = mark_as_seen(new_tenders, seen)
    seen = refresh_statuses(seen)
    save_seen_tenders(seen)
    write_report(new_tenders)
    export_csv(seen)

    open_new = [
        t for t in new_tenders
        if compute_status(normalize_deadline(t.get("deadline", ""))) != "Closed"
    ]
    if category_filter:
        from filters import categorize_tender
        open_new = [t for t in open_new if categorize_tender(t) == category_filter]

    if open_new:
        notify_new_tenders(open_new)

    print(f"\nDone! {len(new_tenders)} nuova/e gara/e.")
    return len(open_new)


if __name__ == "__main__":
    main()
