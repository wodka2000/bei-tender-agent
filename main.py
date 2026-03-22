"""
BEI Tender Agent - Main entry point.

Fetches legal/consulting tenders from the TED API,
filters for Italy, EU and MENA countries,
identifies new ones, and generates a Markdown report.
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


def main():
    print("=== BEI Tender Agent ===\n")

    # 1. Fetch tenders from TED
    print("[1/6] Fetching tenders from TED API...")
    ted_tenders = fetch_tenders_from_ted()
    print(f"      TED tenders fetched: {len(ted_tenders)}")

    # 2. Fetch tenders from EIB
    print("[2/6] Fetching tenders from EIB API...")
    eib_tenders = fetch_eib_tenders()
    print(f"      EIB tenders fetched: {len(eib_tenders)}")

    # 3. Fetch tenders from World Bank
    print("[3/6] Fetching tenders from World Bank API...")
    wb_tenders = fetch_worldbank_tenders()
    print(f"      World Bank tenders fetched: {len(wb_tenders)}")

    # 4. Fetch tenders from ANAC (Italian public procurement)
    print("[4/6] Fetching tenders from ANAC API...")
    anac_tenders = fetch_anac_tenders()
    print(f"      ANAC tenders fetched: {len(anac_tenders)}")

    # 5. Fetch tenders from Bahrain Tender Board
    print("[5/6] Fetching tenders from Bahrain Tender Board...")
    bahrain_tenders = fetch_bahrain_tenders()
    print(f"      Bahrain tenders fetched: {len(bahrain_tenders)}")

    # 6. Fetch tenders from Tunisia HAICOP
    print("[6/6] Fetching tenders from Tunisia HAICOP...")
    tunisia_tenders = fetch_tunisia_tenders()
    print(f"      Tunisia tenders fetched: {len(tunisia_tenders)}")

    # 7. Filter TED by country and relevance (other sources skip this)
    print("[7/8] Filtering TED tenders by country and relevance...")
    relevant = (
        filter_tenders(ted_tenders)
        + eib_tenders + wb_tenders + anac_tenders
        + bahrain_tenders + tunisia_tenders
    )
    print(f"      Relevant tenders: {len(relevant)}")

    # 8. Load seen tenders
    print("[8/9] Loading previously seen tenders...")
    seen = load_seen_tenders()
    print(f"      Previously seen: {len(seen)}")

    # 9. Find new tenders
    new_tenders = find_new_tenders(relevant, seen)
    print(f"      New tenders: {len(new_tenders)}")

    # 10. Update storage and write report
    print("[9/9] Updating storage and writing report...")
    if new_tenders:
        seen = mark_as_seen(new_tenders, seen)
    seen = refresh_statuses(seen)
    save_seen_tenders(seen)
    write_report(new_tenders)
    export_csv(seen)
    print(f"      Report written to {REPORT_PATH}")
    print(f"      CSV exported to {CSV_PATH} ({len(seen)} tenders)")

    # Notifica solo i tender non scaduti
    open_new = [
        t for t in new_tenders
        if compute_status(normalize_deadline(t.get("deadline", ""))) != "Closed"
    ]
    if open_new:
        print(f"[*] Sending Telegram notifications ({len(open_new)} open)...")
        notify_new_tenders(open_new)

    print(f"\nDone! Found {len(new_tenders)} new tender(s).")


if __name__ == "__main__":
    main()
