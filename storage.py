"""Storage module: manages seen tenders and report generation."""

import csv
import json
import os
from datetime import date, datetime

from config import SEEN_TENDERS_PATH, IGNORED_TENDERS_PATH, REPORT_PATH, CSV_PATH
from filters import categorize_tender


def normalize_deadline(raw: str) -> str:
    """Extract YYYY-MM-DD from various TED deadline formats."""
    if not raw or raw == "N/A":
        return ""
    return raw[:10]  # works for both "2024-01-19+01:00" and "2024-01-19T11:00:00+01:00"


def compute_status(deadline_str: str) -> str:
    """Return 'Open', 'Closed', or 'Unknown' based on deadline vs today."""
    if not deadline_str:
        return "Unknown"
    try:
        dl = date.fromisoformat(deadline_str)
        return "Open" if dl >= date.today() else "Closed"
    except ValueError:
        return "Unknown"


def load_seen_tenders() -> dict:
    """Load previously seen tender IDs from JSON file."""
    if not os.path.exists(SEEN_TENDERS_PATH):
        return {}
    try:
        with open(SEEN_TENDERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_seen_tenders(seen: dict) -> None:
    """Save seen tender IDs to JSON file."""
    os.makedirs(os.path.dirname(SEEN_TENDERS_PATH), exist_ok=True)
    with open(SEEN_TENDERS_PATH, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2, ensure_ascii=False)


def load_ignored_tenders() -> set:
    """Load the set of ignored tender IDs."""
    if not os.path.exists(IGNORED_TENDERS_PATH):
        return set()
    try:
        with open(IGNORED_TENDERS_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, IOError):
        return set()


def save_ignored_tenders(ignored: set) -> None:
    """Persist the set of ignored tender IDs."""
    os.makedirs(os.path.dirname(IGNORED_TENDERS_PATH), exist_ok=True)
    with open(IGNORED_TENDERS_PATH, "w", encoding="utf-8") as f:
        json.dump(list(ignored), f, ensure_ascii=False)


def mark_tender_ignored(tender_id: str) -> None:
    """Add a tender ID to the ignored set."""
    ignored = load_ignored_tenders()
    ignored.add(tender_id)
    save_ignored_tenders(ignored)


def find_new_tenders(tenders: list[dict], seen: dict) -> list[dict]:
    """Return only tenders not previously seen."""
    new = []
    for t in tenders:
        tid = t.get("id", "")
        if tid and tid not in seen:
            new.append(t)
    return new


def mark_as_seen(tenders: list[dict], seen: dict) -> dict:
    """Add tenders to the seen dict with a timestamp and full details."""
    now = datetime.now().isoformat()
    for t in tenders:
        tid = t.get("id", "")
        if tid:
            deadline = normalize_deadline(t.get("deadline", ""))
            seen[tid] = {
                "title": t.get("title", ""),
                "buyer": t.get("buyer", ""),
                "country": t.get("country", ""),
                "cpv_codes": t.get("cpv", ""),
                "deadline": deadline,
                "status": compute_status(deadline),
                "publication_date": t.get("publication_date", ""),
                "source_url": t.get("link", ""),
                "source": t.get("source", "TED"),
                "category": categorize_tender(t),
                "first_seen": now,
            }
    return seen


def refresh_statuses(seen: dict) -> dict:
    """Recompute status for all tenders (also normalizes legacy deadlines and fixes URLs)."""
    for tid, info in seen.items():
        info["deadline"] = normalize_deadline(info.get("deadline", ""))
        info["status"] = compute_status(info["deadline"])
        # Fix World Bank URLs — correct format is /procurement-detail/{ID}
        if tid.startswith("WB-") and "/procurement-detail/" not in info.get("source_url", ""):
            notice_id = tid[3:]  # strip "WB-" prefix
            info["source_url"] = (
                f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}"
            )
        # Assign category if missing
        if not info.get("category"):
            info["category"] = categorize_tender({
                "cpv": info.get("cpv_codes", ""),
                "title": info.get("title", ""),
                "buyer": info.get("buyer", ""),
            })
    return seen


def write_report(new_tenders: list[dict]) -> None:
    """Write a Markdown report of new tenders to output/report.md."""
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"# Tender Report",
        f"",
        f"Generated: {now}",
        f"",
    ]

    if not new_tenders:
        lines.append("No new tenders found since last run.")
    else:
        lines.append(f"**{len(new_tenders)} new tender(s) found:**")
        lines.append("")
        for t in new_tenders:
            lines.append(f"## {t.get('title', 'N/A')}")
            lines.append("")
            lines.append(f"- **Source:** {t.get('source', 'N/A')}")
            lines.append(f"- **Buyer:** {t.get('buyer', 'N/A')}")
            lines.append(f"- **Country:** {t.get('country', 'N/A')}")
            lines.append(f"- **Deadline:** {t.get('deadline', 'N/A')}")
            lines.append(f"- **CPV:** {t.get('cpv', 'N/A')}")
            lines.append(f"- **Link:** [{t.get('id', '')}]({t.get('link', '')})")
            lines.append("")
            lines.append("---")
            lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def export_csv(seen: dict) -> None:
    """Export all seen tenders to a CSV file (UTF-8 with BOM, semicolon separator)."""
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)

    fieldnames = [
        "id", "title", "buyer", "country",
        "cpv_codes", "deadline", "status", "publication_date", "source_url",
        "source",
    ]

    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for tid, info in seen.items():
            writer.writerow({
                "id": tid,
                "title": info.get("title", ""),
                "buyer": info.get("buyer", ""),
                "country": info.get("country", ""),
                "cpv_codes": info.get("cpv_codes", ""),
                "deadline": info.get("deadline", ""),
                "status": info.get("status", ""),
                "publication_date": info.get("publication_date", ""),
                "source_url": info.get("source_url", ""),
                "source": info.get("source", "TED"),
            })
