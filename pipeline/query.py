"""Query the regulation map.

Usage:
    py pipeline/query.py "2025/2546 art 5"        # article text + edges + annotations
    py pipeline/query.py "956 article 2a"
    py pipeline/query.py "7552 madde 9"
    py pipeline/query.py --doc 2025/2551          # document overview
    py pipeline/query.py --cited-by "2025/2551 annex II"   # who points here
    py pipeline/query.py "2546 art 5" --full      # untruncated text
"""
import argparse
import re
import sqlite3
import sys
from common import DB_PATH

sys.stdout.reconfigure(encoding="utf-8")


def resolve_doc(con, fragment):
    frag = fragment.strip().replace("\\", "/")
    rows = con.execute("SELECT id, act_key, role FROM documents").fetchall()
    hits = [r for r in rows if frag in r[0] or (r[1] and frag in r[1])]
    if not hits:
        # match on trailing number: '956' -> 2023/956
        hits = [r for r in rows if r[1] and r[1].split("/")[-1] == frag]
    return hits


def find_unit(con, doc_id, unit_frag):
    uf = unit_frag.strip().lower()
    uf = re.sub(r"^art(icle)?\.?\s*", "article ", uf)
    uf = re.sub(r"^madde\s*", "madde ", uf)
    rows = con.execute("SELECT label, unit_type, text FROM units WHERE doc_id=?",
                       (doc_id,)).fetchall()
    exact = [r for r in rows if r[0].lower() == uf]
    if exact:
        return exact
    return [r for r in rows if uf in r[0].lower()]


def show_unit(con, doc_id, label, text, full):
    print(f"\n=== {doc_id} — {label} ===\n")
    body = text if full else (text[:2500] + f"\n[... truncated, {len(text):,} chars total — use --full]"
                              if len(text) > 2500 else text)
    print(body)
    # annotations: unit-specific and document-level
    for (note, src) in con.execute(
            "SELECT note, source FROM annotations WHERE doc_id=? AND (unit_label=? OR unit_label IS NULL)",
            (doc_id, label)):
        print(f"\n[ANNOTATION] {note}\n  (source: {src})")
    out = con.execute(
        "SELECT to_key, to_doc, to_unit, raw, COUNT(*) FROM edges "
        "WHERE from_doc=? AND from_unit=? AND internal=0 GROUP BY to_key, to_unit",
        (doc_id, label)).fetchall()
    if out:
        print("\n--- cites ---")
        for to_key, to_doc, to_unit, raw, n in out:
            tgt = to_doc or f"(untracked: {to_key})"
            print(f"  -> {tgt}" + (f" · {to_unit}" if to_unit else "") + (f"  ×{n}" if n > 1 else ""))
    inc = con.execute(
        "SELECT from_doc, from_unit, COUNT(*) FROM edges "
        "WHERE to_doc=? AND internal=0 AND (to_unit LIKE ? OR ? = '') "
        "GROUP BY from_doc, from_unit", (doc_id, f"%{label}%", label)).fetchall()
    if inc:
        print("\n--- cited by (this unit) ---")
        for fd, fu, n in inc:
            print(f"  <- {fd} · {fu}" + (f"  ×{n}" if n > 1 else ""))


def doc_overview(con, doc_id):
    d = con.execute("SELECT id, jurisdiction, regime, role, status, unit_count, act_key "
                    "FROM documents WHERE id=?", (doc_id,)).fetchone()
    print(f"\n=== {d[0]} ({d[1]}, {d[2]}, {d[4]}) ===\n{d[3]}\nUnits: {d[5]}  act_key: {d[6]}")
    inb = con.execute("SELECT from_doc, COUNT(*) FROM edges WHERE to_doc=? AND internal=0 "
                      "AND rel_type='cites' GROUP BY from_doc ORDER BY 2 DESC", (doc_id,)).fetchall()
    if inb:
        print("\nCited by:")
        for fd, n in inb:
            print(f"  <- {fd}  ×{n}")
    outb = con.execute("SELECT COALESCE(to_doc, '(untracked) '||to_key), COUNT(*) FROM edges "
                       "WHERE from_doc=? AND internal=0 AND rel_type='cites' "
                       "GROUP BY 1 ORDER BY 2 DESC LIMIT 15",
                       (doc_id,)).fetchall()
    if outb:
        print("\nCites:")
        for td, n in outb:
            print(f"  -> {td}  ×{n}")
    for (label,) in con.execute("SELECT DISTINCT unit_label FROM annotations WHERE doc_id=?", (doc_id,)):
        pass
    anns = con.execute("SELECT unit_label, note FROM annotations WHERE doc_id=?", (doc_id,)).fetchall()
    if anns:
        print("\nAnnotations:")
        for ul, note in anns:
            print(f"  [{ul or 'document'}] {note[:160]}{'…' if len(note) > 160 else ''}")
    rels = con.execute("SELECT from_doc, to_doc, rel_type, COALESCE(raw,'') FROM edges "
                       "WHERE rel_type != 'cites' AND (from_doc=? OR to_doc=?)",
                       (doc_id, doc_id)).fetchall()
    if rels:
        print("\nRelations:")
        for fd, td, rt, note in rels:
            print(f"  {fd} —{rt}→ {td}: {note[:120]}")
    instr = con.execute(
        "SELECT i.id, i.name_en, di.role, i.status FROM doc_instrument di "
        "JOIN instruments i ON i.id = di.instrument_id WHERE di.doc_id=?",
        (doc_id,)).fetchall()
    if instr:
        print("\nInstruments:")
        for iid, name, role, status in instr:
            print(f"  {iid} ({status}) — this document is its {role}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref", nargs="?", help="e.g. '2025/2546 art 5'")
    ap.add_argument("--doc", help="document overview by number/id fragment")
    ap.add_argument("--cited-by", dest="cited_by", help="who cites this doc/unit")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()
    con = sqlite3.connect(DB_PATH)

    if args.doc:
        for hit in resolve_doc(con, args.doc):
            doc_overview(con, hit[0])
        return

    target = args.cited_by or args.ref
    if not target:
        ap.print_help()
        return
    m = re.match(r"^\s*([\w./-]+)\s+(.+)$", target)
    doc_frag, unit_frag = (m.group(1), m.group(2)) if m else (target, None)
    hits = resolve_doc(con, doc_frag)
    if not hits:
        print(f"No tracked document matches '{doc_frag}'. Try --doc with a CELEX number fragment.")
        return
    if len(hits) > 1:
        print("Ambiguous:", ", ".join(h[0] for h in hits))
        return
    doc_id = hits[0][0]
    if not unit_frag:
        doc_overview(con, doc_id)
        return
    if args.cited_by:
        rows = con.execute(
            "SELECT from_doc, from_unit, raw FROM edges WHERE to_doc=? AND to_unit LIKE ? AND internal=0",
            (doc_id, f"%{unit_frag}%")).fetchall()
        print(f"\nReferences into {doc_id} · {unit_frag}:")
        for fd, fu, raw in rows:
            print(f"  <- {fd} · {fu}   ({raw})")
        return
    units = find_unit(con, doc_id, unit_frag)
    if not units:
        print(f"No unit matching '{unit_frag}' in {doc_id}. Labels look like 'Article 5', 'Annex II', 'Madde 9'.")
        return
    for label, utype, text in units[:3]:
        show_unit(con, doc_id, label, text, args.full)


if __name__ == "__main__":
    main()
