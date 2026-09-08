"""Harvest typed EU relations from the publications office (CELLAR) - metadata only.

Bound by the design invariant (design/05 #13): relations are harvested ONLY for EU
documents that are members of a tracked instrument. No recursive graph walk.

Per document: amendments (in), legal-basis children (in) = the implements-tree,
completing delegated acts (in), corrigenda (in), consolidated snapshots (in),
pending amendment proposals (in), repeals (both directions).

Output: corpus/eu/cellar_relations.json (committed; build_db.py loads it).
Usage: py pipeline/harvest_eu.py
"""
import datetime
import json
import re
import time
from common import ROOT, load_manifest, sparql_select

OUT = ROOT / "corpus" / "eu" / "cellar_relations.json"
XSD = "^^<http://www.w3.org/2001/XMLSchema#string>"
CDM = "PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>\n"

# relation name -> (CDM property, direction). "in": ?x prop ?work
RELATIONS = {
    "amends_in": ("cdm:resource_legal_amends_resource_legal", "in"),
    "based_on_in": ("cdm:resource_legal_based_on_resource_legal", "in"),
    "completes_in": ("cdm:resource_legal_completes_resource_legal", "in"),
    "corrects_in": ("cdm:resource_legal_corrects_resource_legal", "in"),
    "consolidates_in": ("cdm:act_consolidated_consolidates_resource_legal", "in"),
    "proposes_in": ("cdm:resource_legal_proposes_to_amend_resource_legal", "in"),
    "repeals_out": ("cdm:resource_legal_repeals_resource_legal", "out"),
    "repeals_in": ("cdm:resource_legal_repeals_resource_legal", "in"),
}


def base_celex(celex):
    m = re.match(r"0(\d{4}[RLD]\d{4})", celex)
    return f"3{m.group(1)}" if m else celex


def rel_query(celex, prop, direction):
    triple = (f"?x {prop} ?w ." if direction == "in" else f"?w {prop} ?x .")
    return (CDM +
            f"SELECT DISTINCT ?cx ?d WHERE {{\n"
            f"  ?w cdm:resource_legal_id_celex '{celex}'{XSD} .\n"
            f"  {triple}\n"
            f"  ?x cdm:resource_legal_id_celex ?cx .\n"
            f"  OPTIONAL {{ ?x cdm:work_date_document ?d }}\n"
            f"}} ORDER BY ?d LIMIT 500")


TITLE_Q = (CDM +
           "SELECT ?t WHERE {{\n"
           "  ?w cdm:resource_legal_id_celex '{celex}'" + XSD + " .\n"
           "  ?e cdm:expression_belongs_to_work ?w .\n"
           "  ?e cdm:expression_uses_language "
           "<http://publications.europa.eu/resource/authority/language/ENG> .\n"
           "  ?e cdm:expression_title ?t .\n"
           "}} LIMIT 1")


def fetch_title(celex):
    try:
        rows = sparql_select(TITLE_Q.format(celex=celex), timeout=60)
        return rows[0]["t"]["value"] if rows else None
    except Exception:
        return None


def keep(celex, rel):
    """Sector filter per design/02: legislation (3) for act relations; proposals (5)
    only for the pending panel; consolidated snapshots (0) for versions.
    Corrigenda keep their R(nn) form and attach to the parent."""
    if rel == "proposes_in":
        return celex.startswith("5")
    if rel == "consolidates_in":
        return celex.startswith("0")
    if rel == "corrects_in":
        return "R(" in celex
    return celex.startswith("3") and re.match(r"3\d{4}[RLD]\d{4}$", celex)


def main():
    man = load_manifest()
    atlas = json.loads((ROOT / "instruments.json").read_text(encoding="utf-8"))
    member_docs = {m["doc"] for m in atlas.get("memberships", [])}
    targets = [d for d in man["documents"]
               if d["id"] in member_docs and d.get("celex")]
    result = {"run": datetime.date.today().isoformat(), "docs": {}, "dropped": {}, "titles": {}}
    for doc in targets:
        celex = base_celex(doc["celex"])
        rels, dropped = {}, 0
        for rel, (prop, direction) in RELATIONS.items():
            rows = sparql_select(rel_query(celex, prop, direction))
            entries = []
            for b in rows:
                cx = b["cx"]["value"]
                if not keep(cx, rel):
                    dropped += 1
                    continue
                entries.append({"celex": cx, "date": b.get("d", {}).get("value")})
            rels[rel] = entries
            time.sleep(0.2)
        result["docs"][doc["id"]] = rels
        result["dropped"][doc["id"]] = dropped
        counts = {k: len(v) for k, v in rels.items() if v}
        print(f"{doc['id']} ({celex}): {counts} | dropped {dropped}")
    # titles for every sector-3 act discovered
    discovered = sorted({e["celex"] for rels in result["docs"].values()
                         for rel in ("amends_in", "based_on_in", "completes_in",
                                     "repeals_out", "repeals_in")
                         for e in rels.get(rel, [])})
    for cx in discovered:
        result["titles"][cx] = fetch_title(cx)
        time.sleep(0.2)
    got = sum(1 for t in result["titles"].values() if t)
    print(f"titles: {got}/{len(discovered)} resolved")
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
