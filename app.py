"""BEI Tender Agent - Flask web app."""

import os

from flask import Flask, render_template, request

from storage import load_seen_tenders
from config import TARGET_COUNTRIES, TARGET_BUYERS

app = Flask(__name__)

# Country options for the select dropdown (code -> label)
COUNTRY_OPTIONS = {code: name for code, name in sorted(TARGET_COUNTRIES.items(), key=lambda x: x[1])}


def _apply_filters(rows, args):
    """Filter rows in-place based on query-string parameters (AND logic)."""
    country = args.get("country", "")
    buyer = args.get("buyer", "").strip().lower()
    cpv_types = args.getlist("cpv_type")  # list: "legal", "consulting"
    date_from = args.get("date_from", "")
    date_to = args.get("date_to", "")
    only_eib = args.get("only_eib") == "1"
    only_open = args.get("only_open") == "1"

    filtered = []
    for t in rows:
        # Country filter
        if country and country not in t["country"]:
            continue

        # Buyer free-text filter
        if buyer and buyer not in t["buyer"].lower():
            continue

        # CPV type filter (legal services only: 791xx)
        if cpv_types:
            cpv = t["cpv_codes"]
            match = False
            if "legal" in cpv_types and any(c.strip().startswith("791") for c in cpv.split(",")):
                match = True
            if not match:
                continue

        # Publication date range
        pub = t["publication_date"]
        if date_from and pub and pub < date_from:
            continue
        if date_to and pub and pub > date_to:
            continue

        # Only EIB/BEI buyers
        if only_eib:
            b = t["buyer"].lower()
            if not any(tb in b for tb in TARGET_BUYERS):
                continue

        # Only open tenders
        if only_open and t.get("status") != "Open":
            continue

        filtered.append(t)

    return filtered


@app.route("/")
def index():
    tenders = load_seen_tenders()
    rows = []
    for tid, info in tenders.items():
        rows.append({
            "id": tid,
            "title": info.get("title", ""),
            "buyer": info.get("buyer", ""),
            "country": info.get("country", ""),
            "cpv_codes": info.get("cpv_codes", ""),
            "deadline": info.get("deadline", ""),
            "publication_date": info.get("publication_date", ""),
            "source_url": info.get("source_url", ""),
            "status": info.get("status", "Unknown"),
            "source": info.get("source", "TED"),
        })

    rows = _apply_filters(rows, request.args)

    # Sorting
    sortable = {"title", "buyer", "country", "deadline", "publication_date", "status", "source"}
    sort_col = request.args.get("sort", "publication_date")
    if sort_col not in sortable:
        sort_col = "publication_date"
    direction = request.args.get("direction", "desc")
    if direction not in ("asc", "desc"):
        direction = "desc"
    rows.sort(
        key=lambda t: (t.get(sort_col) or ""),
        reverse=(direction == "desc"),
    )

    return render_template(
        "index.html",
        tenders=rows,
        countries=COUNTRY_OPTIONS,
        sort=sort_col,
        direction=direction,
        # Pass current filter values back to the template
        f_country=request.args.get("country", ""),
        f_buyer=request.args.get("buyer", ""),
        f_cpv_types=request.args.getlist("cpv_type"),
        f_date_from=request.args.get("date_from", ""),
        f_date_to=request.args.get("date_to", ""),
        f_only_eib=request.args.get("only_eib") == "1",
        f_only_open=request.args.get("only_open") == "1",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
