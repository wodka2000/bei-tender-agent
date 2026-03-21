"""
BEI Tender Agent - Main entry point.

Fetches legal/consulting tenders from the TED API,
filters for Italy, EU and MENA countries,
identifies new ones, and generates a Markdown report.
"""

from scraper import fetch_tenders_from_ted, fetch_eib_tenders
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

    # 3. Filter TED by country and relevance (EIB tenders skip this)
    print("[3/6] Filtering TED tenders by country and relevance...")
    relevant = filter_tenders(ted_tenders) + eib_tenders
    print(f"      Relevant tenders: {len(relevant)}")

    # 4. Load seen tenders
    print("[4/6] Loading previously seen tenders...")
    seen = load_seen_tenders()
    print(f"      Previously seen: {len(seen)}")

    # 5. Find new tenders
    print("[5/6] Identifying new tenders...")
    new_tenders = find_new_tenders(relevant, seen)
    print(f"      New tenders: {len(new_tenders)}")

    # 6. Update storage and write report
    print("[6/6] Updating storage and writing report...")
    if new_tenders:
        seen = mark_as_seen(new_tenders, seen)
    seen = refresh_statuses(seen)
    save_seen_tenders(seen)
    write_report(new_tenders)
    export_csv(seen)
    print(f"      Report written to {REPORT_PATH}")
    print(f"      CSV exported to {CSV_PATH} ({len(seen)} tenders)")

    # 7. Send Telegram notifications for new tenders
    if new_tenders:
        print("[7/6] Sending Telegram notifications...")
        notify_new_tenders(new_tenders)

    print(f"\nDone! Found {len(new_tenders)} new tender(s).")


if __name__ == "__main__":
    main()
