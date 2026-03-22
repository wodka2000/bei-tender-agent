"""BEI Tender Agent - Flask web app."""

import os

from flask import Flask, render_template, request

from storage import load_seen_tenders
from config import TARGET_COUNTRIES, CATEGORIES, KNOWN_SOURCES

app = Flask(__name__)

COUNTRY_OPTIONS = {code: name for code, name in sorted(TARGET_COUNTRIES.items(), key=lambda x: x[1])}
CATEGORY_OPTIONS = sorted(CATEGORIES.keys()) + ["Altro"]


def _apply_filters(rows, args):
    country = args.get("country", "")
    buyer = args.get("buyer", "").strip().lower()
    category = args.get("category", "")
    source = args.get("source", "")
    date_from = args.get("date_from", "")
    date_to = args.get("date_to", "")
    only_open = args.get("only_open") == "1"

    filtered = []
    for t in rows:
        if country and country not in t["country"]:
            continue
        if buyer and buyer not in t["buyer"].lower():
            continue
        if category and t.get("category", "") != category:
            continue
        if source and t.get("source", "") != source:
            continue
        pub = t["publication_date"]
        if date_from and pub and pub < date_from:
            continue
        if date_to and pub and pub > date_to:
            continue
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
            "category": info.get("category", "Altro"),
        })

    rows = _apply_filters(rows, request.args)

    sortable = {"title", "buyer", "country", "deadline", "publication_date", "status", "source", "category"}
    sort_col = request.args.get("sort", "publication_date")
    if sort_col not in sortable:
        sort_col = "publication_date"
    direction = request.args.get("direction", "desc")
    if direction not in ("asc", "desc"):
        direction = "desc"
    rows.sort(key=lambda t: (t.get(sort_col) or ""), reverse=(direction == "desc"))

    return render_template(
        "index.html",
        tenders=rows,
        countries=COUNTRY_OPTIONS,
        categories=CATEGORY_OPTIONS,
        sources=KNOWN_SOURCES,
        sort=sort_col,
        direction=direction,
        f_country=request.args.get("country", ""),
        f_buyer=request.args.get("buyer", ""),
        f_category=request.args.get("category", ""),
        f_source=request.args.get("source", ""),
        f_date_from=request.args.get("date_from", ""),
        f_date_to=request.args.get("date_to", ""),
        f_only_open=request.args.get("only_open") == "1",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
