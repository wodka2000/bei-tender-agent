"""Configuration for the tender monitoring agent."""

import os

from dotenv import load_dotenv

load_dotenv()

# Telegram Bot credentials (set in .env)
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# TED API (Tenders Electronic Daily) - no authentication required
TED_API_URL = "https://api.ted.europa.eu/v3/notices/search"

# EIB procurement API (internal JSON endpoint, no auth required)
EIB_PROCUREMENT_API = "https://www.eib.org/provider-eib/app/list/medias/procurements"
EIB_DETAIL_URL = "https://www.eib.org/en/about/procurement/calls/all/{id}"

# World Bank procurement API (no auth required)
WORLDBANK_API_URL = "https://search.worldbank.org/api/v2/procnotices"
# World Bank country names for our target countries (WB uses full names, not ISO codes)
WORLDBANK_TARGET_COUNTRIES = [
    # From TARGET_COUNTRIES values + WB-specific aliases
    "Italy", "Luxembourg", "Belgium",
    "Saudi Arabia", "Jordan", "Iraq", "Syrian Arab Republic", "Syria",
    "Egypt", "Oman", "United Arab Emirates", "Kuwait", "Bahrain",
    "Qatar", "Lebanon", "Libya", "Tunisia", "Morocco", "Algeria",
    "Yemen", "West Bank and Gaza", "Palestine",
]

# ANAC (Italian National Anti-Corruption Authority) open data API
ANAC_API_URL = "https://dati.anticorruzione.it/opendata/ocds/api/bandi"
# Legal keywords in Italian for ANAC query
ANAC_LEGAL_KEYWORDS = ["giuridic", "legale", "legali", "avvocato", "studio legale", "arbitrat"]

# Bahrain Tender Board (undocumented public AJAX endpoint, no auth)
BAHRAIN_TENDERS_URL = "https://etendering.tenderboard.gov.bh/Tenders/publicDash"
BAHRAIN_DETAIL_URL = "https://etendering.tenderboard.gov.bh/Tenders/nitParameterView?mode=public&tenderNo={ref}"

# Tunisia HAICOP (marchespublics.gov.tn — DataTable AJAX, no auth)
TUNISIA_TENDERS_URL = "https://www.marchespublics.gov.tn/fr/appels-doffres"

# Italian keywords for TED full-text search (FT operator)
TEXT_KEYWORDS_IT = ["giuridico", "giuridiche", "giuridica", "giuridici"]

# CPV codes — legal services only (no 794xx management/consulting)
CPV_CODES = [
    "79100000",  # Legal services
    "79110000",  # Legal advisory and representation services
    "79111000",  # Legal advisory services
    "79112000",  # Legal representation services
    "79120000",  # Patent and copyright consultancy
    "79130000",  # Legal documentation and certification services
    "79140000",  # Legal advisory and information services
]

# Target countries - ISO 3166-1 alpha-3 codes as used by TED API
TARGET_COUNTRIES = {
    # Italy
    "ITA": "Italy",
    # EU institutions (Luxembourg-based, Belgium-based, etc.)
    "LUX": "Luxembourg",
    "BEL": "Belgium",
    # MENA countries
    "SAU": "Saudi Arabia",
    "JOR": "Jordan",
    "IRQ": "Iraq",
    "SYR": "Syria",
    "EGY": "Egypt",
    "OMN": "Oman",
    "ARE": "United Arab Emirates",
    "KWT": "Kuwait",
    "BHR": "Bahrain",
    "QAT": "Qatar",
    "LBN": "Lebanon",
    "LBY": "Libya",
    "TUN": "Tunisia",
    "MAR": "Morocco",
    "DZA": "Algeria",
    "YEM": "Yemen",
    "PSE": "Palestine",
}

# Buyers of interest (institutions)
TARGET_BUYERS = [
    # Gruppo BEI
    "european investment bank",
    "eib",
    "banca europea per gli investimenti",
    "banque européenne d'investissement",
    "bei",
    "european investment fund",
    "eif",
    # Banche multilaterali e IFI
    "european bank for reconstruction and development",
    "ebrd",
    "world bank",
    "international bank for reconstruction and development",
    "ibrd",
    "international development association",
    "ida",
    "international finance corporation",
    "ifc",
    "african development bank",
    "afdb",
    # Istituzioni UE / esterne
    "european commission",
    "european union",
    "eu external action service",
    "eeas",
    "delegation of the european union",
    "eu delegation",
    # Sistema ONU
    "united nations development programme",
    "undp",
    "united nations office for project services",
    "unops",
]

# Keywords for legal services — used by filters.py to keep only lawyer/law-firm tenders
LEGAL_KEYWORDS = [
    "lawyer",
    "attorney",
    "law firm",
    "avvocato",
    "studio legale",
    "legal services",
    "legal advisory",
    "legal representation",
    "litigation",
    "arbitration",
    "dispute resolution",
    "contentious",
    "non-contentious",
    "counsel",
    "external legal services",
    "panel of law firms",
    "framework agreement for legal services",
    "incarico legale",
    "assistenza legale",
]

# TED API response fields to request
TED_FIELDS = [
    "notice-title",
    "organisation-name-buyer",
    "buyer-name",
    "buyer-country",
    "deadline-receipt-tender-date-lot",
    "deadline-receipt-request",
    "classification-cpv",
    "place-of-performance-country-lot",
    "publication-date",
    "notice-type",
]

# File paths
SEEN_TENDERS_PATH = "data/seen_tenders.json"
IGNORED_TENDERS_PATH = "data/ignored_tenders.json"
REPORT_PATH = "output/report.md"
CSV_PATH = "output/tenders.csv"
