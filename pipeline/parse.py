"""Segment corpus documents into units (articles/annexes) and extract citation edges.

Handles three source formats:
  A. EUR-Lex new-act XHTML   (article headings: <p id="art_N" class="oj-ti-art">)
  B. EUR-Lex consolidated    (article headings: <p class="title-article-norm">Article N</p>)
  C. Turkish statutes (txt)  (article headings: MADDE N-)
"""
import re
from common import strip_html

# --- act reference grammar -------------------------------------------------

ACT_RE = re.compile(
    r"(?:Commission\s+)?(?:Implementing\s+|Delegated\s+)?"
    r"(Regulation|Directive|Decision)\s*"
    r"(?:\(EU\)|\(EC\)|\(EEC\))?\s*"
    r"(?:No\s+)?"
    r"(\d{4}/\d{1,4}|\d{1,4}/\d{4})"
    r"(?:/(?:EC|EU|EEC))?"
)

# unit-of-act references, tried longest-first on each act mention's left context
UNIT_PATTERNS = [
    re.compile(r"(Section\s+[\d.]+\s+of\s+Annex\s+[IVXLC]+[a-z]?)\s+to\s*$", re.I),
    re.compile(r"(point\s+[\w().]+\s+of\s+Annex\s+[IVXLC]+[a-z]?)\s+to\s*$", re.I),
    re.compile(r"(Annex(?:es)?\s+[IVXLC]+[a-z]?(?:\s+and\s+[IVXLC]+[a-z]?)?)\s+to\s*$", re.I),
    re.compile(r"(Articles?\s+\d+[a-z]?(?:\(\d+\))?(?:\([a-z]\))?"
               r"(?:(?:,\s*| and )\d+[a-z]?(?:\(\d+\))?)*)\s+of\s*$", re.I),
    re.compile(r"(Chapter\s+[IVXLC]+[a-z]?)\s+of\s*$", re.I),
]

INTERNAL_RE = re.compile(
    r"(?<![a-zA-Z])Article\s+(\d+[a-z]?)(?:\((\d+)\))?(?!\s+(?:of|to)\b)")


def act_key_from_celex(celex):
    """'02023R0956-20251020' or '32025R2546' -> ('regulation','2023/956')."""
    m = re.match(r"[03](\d{4})([RLD])(\d{4})", celex)
    if not m:
        return None
    year, typ, num = m.group(1), m.group(2), int(m.group(3))
    kind = {"R": "regulation", "L": "directive", "D": "decision"}[typ]
    return kind, f"{year}/{num}"


def normalise_act_key(kind, number):
    """Citation text gives e.g. ('Directive','2003/87') or ('Regulation','2018/2066')."""
    a, b = number.split("/")
    if len(a) == 4:
        year, num = a, b
    else:
        year, num = b, a
    return kind.lower(), f"{year}/{int(num)}"


# --- segmentation ----------------------------------------------------------

WS = r"[\s ]"  # EUR-Lex uses non-breaking spaces inside headings
HEADING_RES = {
    "new_act": re.compile(
        rf'<p[^>]*class="oj-ti-art"[^>]*>{WS}*Article{WS}+(\d+[a-z]?){WS}*</p>'),
    "consolidated": re.compile(
        rf'<p[^>]*class="title-article-norm"[^>]*>{WS}*Article{WS}+(\d+[a-z]?){WS}*</p>'),
}
ANNEX_RES = {
    "new_act": re.compile(rf'<p[^>]*class="oj-doc-ti"[^>]*>{WS}*(ANNEX{WS}*[IVXLC]*[a-z]?){WS}*</p>'),
    "consolidated": re.compile(rf'<p[^>]*class="title-annex-1"[^>]*>[^<]*?(ANNEX{WS}*[IVXLC]*[a-z]?)'),
}
TR_ART_RE = re.compile(r"^MADDE\s+(\d+)-", re.M)


def detect_format(raw):
    if 'class="title-article-norm"' in raw:
        return "consolidated"
    if 'class="oj-ti-art"' in raw or 'id="art_' in raw:
        return "new_act"
    return None


def segment_eu(raw):
    fmt = detect_format(raw)
    if fmt is None:
        return None, []
    art_re, annex_re = HEADING_RES[fmt], ANNEX_RES[fmt]
    marks = []  # (pos, unit_type, label)
    for m in art_re.finditer(raw):
        marks.append((m.start(), "article", f"Article {m.group(1)}"))
    for m in annex_re.finditer(raw):
        label = re.sub(r"[\s\xa0]+", " ", m.group(1)).strip()
        label = "Annex" + (" " + label.split(" ", 1)[1].upper() if " " in label else "")
        marks.append((m.start(), "annex", label.strip()))
    marks.sort()
    units = []
    if marks:
        preamble = strip_html(raw[:marks[0][0]])
        if preamble.strip():
            units.append(("preamble", "Preamble", preamble))
    seen = {}
    for i, (pos, utype, label) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(raw)
        text = strip_html(raw[pos:end])
        # consolidated docs repeat annex headings in tables of content; keep longest
        if label in seen:
            if len(text) > len(units[seen[label]][2]):
                units[seen[label]] = (utype, label, text)
            continue
        seen[label] = len(units)
        units.append((utype, label, text))
    return fmt, units


def segment_tr(txt):
    marks = [(m.start(), "article", f"Madde {m.group(1)}") for m in TR_ART_RE.finditer(txt)]
    units = []
    if marks:
        pre = txt[:marks[0][0]].strip()
        if pre:
            units.append(("preamble", "Preamble", pre))
    for i, (pos, utype, label) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(txt)
        units.append((utype, label, txt[pos:end].strip()))
    return "tr_statute", units


# --- citation extraction ---------------------------------------------------

def extract_citations(unit_text, self_key):
    """Returns (edges, mention_count). Edge: dict(to_key, to_unit, raw).
    self_key: ('regulation','2023/956') for internal-reference attribution."""
    edges = []
    mentions = 0
    for m in ACT_RE.finditer(unit_text):
        mentions += 1
        kind, num = m.group(1), m.group(2)
        try:
            to_key = normalise_act_key(kind, num)
        except Exception:
            continue
        left = unit_text[max(0, m.start() - 120):m.start()]
        to_unit, raw_ref = None, m.group(0)
        for pat in UNIT_PATTERNS:
            um = pat.search(left)
            if um:
                to_unit = re.sub(r"\s+", " ", um.group(1)).strip()
                raw_ref = f"{to_unit} of/to {m.group(0)}"
                break
        if to_key == self_key:
            continue  # self-mention of own number in title/preamble
        edges.append({"to_key": f"{to_key[0]}:{to_key[1]}",
                      "to_unit": to_unit, "raw": raw_ref})
    # internal references (Article N without 'of <act>')
    for m in INTERNAL_RE.finditer(unit_text):
        tail = unit_text[m.end():m.end() + 40]
        if re.match(r"\s+of\s+(?:Commission\s+)?(?:Implementing\s+|Delegated\s+)?"
                    r"(?:Regulation|Directive|Decision)", tail):
            continue
        edges.append({"to_key": f"{self_key[0]}:{self_key[1]}" if self_key else "self",
                      "to_unit": f"Article {m.group(1)}", "raw": m.group(0),
                      "internal": True})
    return edges, mentions
