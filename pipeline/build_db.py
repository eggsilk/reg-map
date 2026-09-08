"""Rebuild the SQLite database and INDEX.md from the corpus + curated files.
Fully derived - safe to delete and re-run.

Loads: manifest.json (tracked documents, watch pages, curated doc-doc relations),
instruments.json (atlas layer: instruments, memberships, cross-instrument edges, sources),
annotations.json (expert annotations).

Usage: py pipeline/build_db.py
"""
import json
import sqlite3
import datetime
from common import ROOT, DB_PATH, load_manifest, doc_paths
from parse import segment_eu, segment_tr, extract_citations, act_key_from_celex

ANNOTATIONS = ROOT / "annotations.json"
INSTRUMENTS = ROOT / "instruments.json"
CELLAR_REL = ROOT / "corpus" / "eu" / "cellar_relations.json"
INDEX_MD = ROOT / "INDEX.md"

STATUS_ENUM = ("under_consideration", "under_development", "enabled_not_established",
               "pilot_mandated", "pilot_operational", "in_force", "suspended", "abolished")
DOC_REL_ENUM = ("cites", "legal_basis", "amends", "completes", "corrects", "consolidates",
                "repeals", "proposes_to_amend", "supersedes", "responds_to")
INSTR_REL_ENUM = ("modeled_on", "linked_by_treaty", "responds_to", "replaces")
LICENSE_ENUM = ("cc-by-4.0", "public-law", "copyright-linkout", "manual")

SCHEMA = f"""
CREATE TABLE documents (
  id TEXT PRIMARY KEY, jurisdiction TEXT, regime TEXT, instrument_type TEXT,
  role TEXT, celex TEXT, act_key TEXT, language TEXT, status TEXT, tier TEXT,
  source_url TEXT, flags TEXT, parse_format TEXT, unit_count INTEGER,
  title TEXT, date_document TEXT, metadata_only INTEGER DEFAULT 0, official_id TEXT
);
CREATE TABLE units (
  id INTEGER PRIMARY KEY, doc_id TEXT, unit_type TEXT, label TEXT,
  ordinal INTEGER, text TEXT,
  UNIQUE(doc_id, label)
);
CREATE TABLE edges (
  id INTEGER PRIMARY KEY, from_doc TEXT, from_unit TEXT,
  to_key TEXT, to_doc TEXT, to_unit TEXT, raw TEXT, internal INTEGER DEFAULT 0,
  rel_type TEXT NOT NULL DEFAULT 'cites'
    CHECK (rel_type IN {DOC_REL_ENUM!r}),
  source TEXT, retrieved TEXT
);
CREATE TABLE sources (
  id TEXT PRIMARY KEY, kind TEXT, ref TEXT,
  license TEXT CHECK (license IN {LICENSE_ENUM!r}),
  fetched TEXT
);
CREATE TABLE instruments (
  id TEXT PRIMARY KEY, name_en TEXT NOT NULL, name_local TEXT NOT NULL,
  jurisdiction TEXT NOT NULL,
  instrument_type TEXT CHECK (instrument_type IN ('ets','carbon_tax','border_mechanism','hybrid')),
  status TEXT CHECK (status IN {STATUS_ENUM!r}),
  status_source TEXT REFERENCES sources(id),
  status_basis_doc TEXT, status_basis_unit TEXT,
  last_checked TEXT, publishable INTEGER DEFAULT 0, notes TEXT, unverified TEXT,
  CHECK (publishable = 0 OR (status_source IS NOT NULL AND last_checked IS NOT NULL))
);
CREATE TABLE doc_instrument (
  doc_id TEXT, instrument_id TEXT REFERENCES instruments(id),
  role TEXT CHECK (role IN ('legal_basis','implementing_regulation','delegated_regulation',
                            'amendment','guidance','transposition')),
  UNIQUE(doc_id, instrument_id, role)
);
CREATE TABLE instrument_edges (
  id INTEGER PRIMARY KEY, from_id TEXT REFERENCES instruments(id),
  to_id TEXT REFERENCES instruments(id),
  rel_type TEXT CHECK (rel_type IN {INSTR_REL_ENUM!r}),
  source TEXT, note TEXT, publishable INTEGER DEFAULT 0,
  CHECK (publishable = 0 OR source IS NOT NULL)
);
CREATE TABLE annotations (
  id INTEGER PRIMARY KEY, doc_id TEXT, unit_label TEXT, note TEXT, source TEXT, added TEXT
);
CREATE INDEX idx_units_doc ON units(doc_id);
CREATE INDEX idx_edges_from ON edges(from_doc);
CREATE INDEX idx_edges_todoc ON edges(to_doc);
CREATE INDEX idx_docinstr ON doc_instrument(instrument_id);
"""


def main():
    man = load_manifest()
    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)

    key_map = {}
    for doc in man["documents"]:
        if "celex" in doc:
            k = act_key_from_celex(doc["celex"])
            if k:
                key_map[f"{k[0]}:{k[1]}"] = doc["id"]

    stats = {"docs": 0, "units": 0, "edges": 0, "mentions": 0,
             "instruments": 0, "memberships": 0}
    for doc in man["documents"]:
        html_path, txt_path = doc_paths(doc)
        self_key = act_key_from_celex(doc["celex"]) if "celex" in doc else None
        fmt, units = None, []
        if doc["jurisdiction"] == "EU" and html_path.exists():
            fmt, units = segment_eu(html_path.read_text(encoding="utf-8"))
        elif txt_path.exists():
            fmt, units = segment_tr(txt_path.read_text(encoding="utf-8"))
        con.execute(
            "INSERT INTO documents (id, jurisdiction, regime, instrument_type, role, celex, "
            "act_key, language, status, tier, source_url, flags, parse_format, unit_count, "
            "metadata_only, official_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc["id"], doc["jurisdiction"], doc["regime"], doc["instrument_type"],
             doc.get("role", ""), doc.get("celex"),
             f"{self_key[0]}:{self_key[1]}" if self_key else None,
             doc.get("language", "en"), doc["status"], doc["tier"],
             doc.get("source_url", ""), ",".join(doc.get("flags", [])),
             fmt, len(units), 0, doc.get("celex") or doc.get("source_url", "")))
        stats["docs"] += 1
        for ordinal, (utype, label, text) in enumerate(units):
            con.execute(
                "INSERT OR IGNORE INTO units (doc_id, unit_type, label, ordinal, text) "
                "VALUES (?,?,?,?,?)", (doc["id"], utype, label, ordinal, text))
            stats["units"] += 1
            if doc.get("language", "en") != "en":
                continue
            edges, mentions = extract_citations(text, self_key)
            stats["mentions"] += mentions
            for e in edges:
                to_doc = doc["id"] if e.get("internal") else key_map.get(e["to_key"])
                con.execute(
                    "INSERT INTO edges (from_doc, from_unit, to_key, to_doc, to_unit, raw, "
                    "internal, rel_type, source) VALUES (?,?,?,?,?,?,?,'cites','regex-corpus')",
                    (doc["id"], label, e["to_key"], to_doc, e.get("to_unit"),
                     e["raw"], 1 if e.get("internal") else 0))
                stats["edges"] += 1

    # CELLAR-harvested typed relations (metadata-only broad layer)
    if CELLAR_REL.exists():
        cellar = json.loads(CELLAR_REL.read_text(encoding="utf-8"))
        titles = cellar.get("titles", {})
        run_date = cellar.get("run")

        def ensure_doc(celex):
            """Metadata-only document row for a discovered act; returns doc id."""
            m = __import__("re").match(r"3(\d{4})([RLD])(\d{4})$", celex)
            if not m:
                return None
            year, letter, num = m.group(1), m.group(2), int(m.group(3))
            did = f"eu-{year}-{num}"
            row = con.execute("SELECT celex FROM documents WHERE id=?", (did,)).fetchone()
            if row:
                if row[0] and celex not in row[0]:
                    # same year/number, different act type: disambiguate
                    did = f"eu-{year}-{letter.lower()}{num}"
                    row = con.execute("SELECT 1 FROM documents WHERE id=?", (did,)).fetchone()
                    if row:
                        return did
                else:
                    return did
            kind = {"R": "regulation", "L": "directive", "D": "decision"}[m.group(2)]
            con.execute(
                "INSERT INTO documents (id, jurisdiction, regime, instrument_type, role, celex, "
                "act_key, language, status, tier, metadata_only, title, official_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,1,?,?)",
                (did, "EU", "", kind, "", celex, f"{kind}:{year}/{num}", "en",
                 "unreviewed", "B", titles.get(celex), celex))
            stats["metadata_docs"] = stats.get("metadata_docs", 0) + 1
            return did

        REL_MAP = {  # harvest key -> (rel_type, other act is the FROM side?)
            "amends_in": ("amends", True),
            "based_on_in": ("legal_basis", True),
            "completes_in": ("completes", True),
            "repeals_in": ("repeals", True),
            "repeals_out": ("repeals", False),
        }
        for doc_id, rels in cellar.get("docs", {}).items():
            for key, entries in rels.items():
                if key in REL_MAP:
                    rel_type, other_is_from = REL_MAP[key]
                    for e in entries:
                        other = ensure_doc(e["celex"])
                        if not other or other == doc_id:
                            continue
                        fd, td = (other, doc_id) if other_is_from else (doc_id, other)
                        con.execute(
                            "INSERT INTO edges (from_doc, to_doc, rel_type, source, retrieved, raw) "
                            "VALUES (?,?,?,'src-cellar',?,?)",
                            (fd, td, rel_type, run_date, e["celex"]))
                        stats["cellar_edges"] = stats.get("cellar_edges", 0) + 1
                elif key in ("corrects_in", "consolidates_in", "proposes_in"):
                    rel_type = {"corrects_in": "corrects", "consolidates_in": "consolidates",
                                "proposes_in": "proposes_to_amend"}[key]
                    for e in entries:
                        # endpoint-light: corrigenda, version snapshots and proposals are
                        # badges/panels on the parent, not document nodes (design/02)
                        con.execute(
                            "INSERT INTO edges (from_doc, to_doc, rel_type, source, retrieved, raw) "
                            "VALUES (NULL,?,?,'src-cellar',?,?)",
                            (doc_id, rel_type, run_date, e["celex"]))
                        stats["cellar_edges"] = stats.get("cellar_edges", 0) + 1

    # curated doc-doc relations from the manifest
    for rel in man.get("relations", []):
        con.execute(
            "INSERT INTO edges (from_doc, to_doc, rel_type, source, raw) "
            "VALUES (?,?,?,'manual',?)",
            (rel["from"], rel["to"], rel["rel_type"], rel.get("note", "")))

    # atlas layer
    if INSTRUMENTS.exists():
        atlas = json.loads(INSTRUMENTS.read_text(encoding="utf-8"))
        for s in atlas.get("sources", []):
            con.execute("INSERT INTO sources VALUES (?,?,?,?,?)",
                        (s["id"], s["kind"], s["ref"], s["license"], s.get("fetched")))
        for i in atlas.get("instruments", []):
            con.execute(
                "INSERT INTO instruments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (i["id"], i["name_en"], i["name_local"], i["jurisdiction"],
                 i["instrument_type"], i["status"], i.get("status_source"),
                 i.get("status_basis_doc"), i.get("status_basis_unit"),
                 i.get("last_checked"), i.get("publishable", 0), i.get("notes"),
                 json.dumps(i.get("unverified", []))))
            stats["instruments"] += 1
        for m in atlas.get("memberships", []):
            con.execute("INSERT INTO doc_instrument VALUES (?,?,?)",
                        (m["doc"], m["instrument"], m["role"]))
            stats["memberships"] += 1
        for e in atlas.get("instrument_edges", []):
            con.execute(
                "INSERT INTO instrument_edges (from_id, to_id, rel_type, source, note, publishable) "
                "VALUES (?,?,?,?,?,?)",
                (e["from"], e["to"], e["rel_type"], e.get("source"),
                 e.get("note"), e.get("publishable", 0)))

    if ANNOTATIONS.exists():
        for a in json.loads(ANNOTATIONS.read_text(encoding="utf-8")):
            con.execute("INSERT INTO annotations (doc_id, unit_label, note, source, added) "
                        "VALUES (?,?,?,?,?)",
                        (a["doc_id"], a.get("unit_label"), a["note"],
                         a.get("source", ""), a.get("added", "")))

    con.commit()
    write_index(con, man)
    con.close()
    print(json.dumps(stats, indent=2))


def write_index(con, man):
    lines = ["# Document Index", "",
             f"Generated {datetime.date.today().isoformat()} by build_db.py. "
             "Every tracked document and instrument. The database (db/regmap.db) is derived; "
             "rebuild with `py pipeline/build_db.py`.", ""]
    rows = con.execute("SELECT id, name_en, jurisdiction, instrument_type, status "
                       "FROM instruments ORDER BY jurisdiction, id").fetchall()
    if rows:
        lines += ["## Instruments", "", "| id | name | jurisdiction | type | status |",
                  "|---|---|---|---|---|"]
        for r in rows:
            lines.append("| " + " | ".join(str(x) for x in r) + " |")
        lines.append("")
    for jur in sorted({d["jurisdiction"] for d in man["documents"]}):
        lines += [f"## Documents — {jur}", "",
                  "| id | regime | type | status | role | units | notes |",
                  "|---|---|---|---|---|---|---|"]
        for d in man["documents"]:
            if d["jurisdiction"] != jur:
                continue
            n = con.execute("SELECT unit_count FROM documents WHERE id=?", (d["id"],)).fetchone()[0]
            flags = ", ".join(d.get("flags", []))
            lines.append(f"| {d['id']} | {d['regime']} | {d['instrument_type']} | "
                         f"{d['status']} | {d.get('role','')} | {n} | {flags} |")
        lines.append("")
    rels = con.execute("SELECT from_doc, rel_type, to_doc, raw FROM edges "
                       "WHERE source='manual'").fetchall()
    if rels:
        lines += ["## Curated document relations", ""]
        for fd, rt, td, note in rels:
            lines.append(f"- **{fd}** {rt} **{td}** — {note}")
        lines.append("")
    INDEX_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
