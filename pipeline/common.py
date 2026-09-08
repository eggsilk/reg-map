"""Shared helpers for the reg-map pipeline. Stdlib only."""
import json
import re
import html as htmllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest.json"
CORPUS = ROOT / "corpus"
DB_PATH = ROOT / "db" / "regmap.db"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

EURLEX_HTML = "https://eur-lex.europa.eu/legal-content/{lang}/TXT/HTML/?uri=CELEX:{celex}"
EURLEX_OVERVIEW = "https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX:{celex}"
SPARQL_ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"


def sparql_select(query, timeout=120):
    """Run a SELECT against the EU publications office; returns the bindings list."""
    import json as _json
    import urllib.parse
    url = SPARQL_ENDPOINT + "?" + urllib.parse.urlencode(
        {"query": query, "format": "application/json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return _json.loads(r.read().decode("utf-8"))["results"]["bindings"]


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def doc_paths(doc):
    """corpus/<jurisdiction lowercased>/<id>.html / .txt"""
    d = CORPUS / doc["jurisdiction"].lower()
    return d / f"{doc['id']}.html", d / f"{doc['id']}.txt"


def fetch_url(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def strip_html(raw):
    """HTML -> plain text, whitespace-normalised per paragraph-ish block."""
    txt = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    # block-level closers become newlines so structure survives roughly
    txt = re.sub(r"</(p|div|tr|table|h[1-6]|li)>", "\n", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = htmllib.unescape(txt)
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n\s*", "\n", txt)
    return txt.strip()
