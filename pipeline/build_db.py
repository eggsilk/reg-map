"""Rebuild the SQLite database and INDEX.md from the corpus. Fully derived - safe to delete and re-run.

Usage: py pipeline/build_db.py
"""
import json
import sqlite3
import datetime
from common import ROOT, DB_PATH, load_manifest, doc_paths
from parse import segment_eu, segment_tr, extract_citations, act_key_from_celex

ANNOTATIONS = ROOT / "annotations.json"
INDEX_MD = ROOT / "INDEX.md"

SCHEMA = """
CREATE TABLE documents (
  id TEXT PRIMARY KEY, jurisdiction TEXT, regime TEXT, instrument_type TEXT,
  role TEXT, celex TEXT, act_key TEXT, language TEXT, status TEXT, tier TEXT,
  source_url TEXT, flags TEXT, parse_format TEXT, unit_count INTEGER
);
CREATE TABLE units (
  id INTEGER PRIMARY KEY, doc_id TEXT, unit_type TEXT, label TEXT,
  ordinal INTEGER, text TEXT,
  UNIQUE(doc_id, label)
);
CREATE TABLE edges (
  id INTEGER PRIMARY KEY, from_doc TEXT, from_unit TEXT,
  to_key TEXT, to_doc TEXT, to_unit TEXT, raw TEXT, internal INTEGER DEFAULT 0
);
CREATE TABLE relations (
  id INTEGER PRIMARY KEY, from_doc TEXT, to_doc TEXT, rel_type TEXT, note TEXT
);
CREATE TABLE annotations (
  id INTEGER PRIMARY KEY, doc_id TEXT, unit_label TEXT, note TEXT, source TEXT, added TEXT
);
CREATE INDEX idx_units_doc ON units(doc_id);
CREATE INDEX idx_edges_from ON edges(from_doc);
CREATE INDEX idx_edges_todoc ON edges(to_doc);
"""


def main():
    man = load_manifest()
    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)

    # act_key -> doc id map for edge resolution
    key_map = {}
    for doc in man["documents"]:
        if "celex" in doc:
            k = act_key_from_celex(doc["celex"])
            if k:
                key_map[f"{k[0]}:{k[1]}"] = doc["id"]

    stats = {"docs": 0, "units": 0, "edges": 0, "mentions": 0, "resolved_units": 0}
    for doc in man["documents"]:
        html_path, txt_path = doc_paths(doc)
        self_key = act_key_from_celex(doc["celex"]) if "celex" in doc else None
        fmt, units = None, []
        if doc["jurisdiction"] == "EU" and html_path.exists():
            fmt, units = segment_eu(html_path.read_text(encoding="utf-8"))
        elif txt_path.exists():
            fmt, units = segment_tr(txt_path.read_text(encoding="utf-8"))
        con.execute(
            "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc["id"], doc["jurisdiction"], doc["regime"], doc["instrument_type"],
             doc.get("role", ""), doc.get("celex"),
             f"{self_key[0]}:{self_key[1]}" if self_key else None,
             doc.get("language", "en"), doc["status"], doc["tier"],
             doc.get("source_url", ""), ",".join(doc.get("flags", [])),
             fmt, len(units)))
        stats["docs"] += 1
        for ordinal, (utype, label, text) in enumerate(units):
            con.execute(
                "INSERT OR IGNORE INTO units (doc_id, unit_type, label, ordinal, text) "
                "VALUES (?,?,?,?,?)", (doc["id"], utype, label, ordinal, text))
            stats["units"] += 1
            if doc.get("language", "en") != "en":
                continue  # citation grammar is EN-only for now
            edges, mentions = extract_citations(text, self_key)
            stats["mentions"] += mentions
            for e in edges:
                to_doc = doc["id"] if e.get("internal") else key_map.get(e["to_key"])
                con.execute(
                    "INSERT INTO edges (from_doc, from_unit, to_key, to_doc, to_unit, raw, internal) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (doc["id"], label, e["to_key"], to_doc, e.get("to_unit"),
                     e["raw"], 1 if e.get("internal") else 0))
                stats["edges"] += 1
                if e.get("to_unit"):
                    stats["resolved_units"] += 1

    for rel in man.get("relations", []):
        con.execute("INSERT INTO relations (from_doc, to_doc, rel_type, note) VALUES (?,?,?,?)",
                    (rel["from"], rel["to"], rel["rel_type"], rel.get("note", "")))

    if ANNOTATIONS.exists():
        for a in json.loads(ANNOTATIONS.read_text(encoding="utf-8")):
            con.execute("INSERT INTO annotations (doc_id, unit_label, note, source, added) "
                        "VALUES (?,?,?,?,?)",
                        (a["doc_id"], a.get("unit_label"), a["note"],
                         a.get("source", ""), a.get("added", "")))

    con.commit()
    write_index(con, man)
    con.close()
    ext = con  # noqa - keep linters quiet
    print(json.dumps(stats, indent=2))


def write_index(con, man):
    lines = ["# Document Index", "",
             f"Generated {datetime.date.today().isoformat()} by build_db.py. "
             "Every tracked document, by jurisdiction. The database (db/regmap.db) is derived "
             "from the corpus and this manifest; rebuild with `py pipeline/build_db.py`.", ""]
    for jur in sorted({d["jurisdiction"] for d in man["documents"]}):
        lines.append(f"## {jur}")
        lines.append("")
        lines.append("| id | regime | type | status | role | units | notes |")
        lines.append("|---|---|---|---|---|---|---|")
        for d in man["documents"]:
            if d["jurisdiction"] != jur:
                continue
            n = con.execute("SELECT unit_count FROM documents WHERE id=?", (d["id"],)).fetchone()[0]
            flags = ", ".join(d.get("flags", []))
            lines.append(f"| {d['id']} | {d['regime']} | {d['instrument_type']} | "
                         f"{d['status']} | {d.get('role','')} | {n} | {flags} |")
        lines.append("")
    if man.get("relations"):
        lines.append("## Cross-document relations (curated)")
        lines.append("")
        for r in man["relations"]:
            lines.append(f"- **{r['from']}** {r['rel_type']} **{r['to']}** — {r.get('note','')}")
        lines.append("")
    INDEX_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
