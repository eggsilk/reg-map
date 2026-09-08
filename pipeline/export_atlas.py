"""Export the atlas layer for the website. Enforces the mechanical rubric rules
(design/03): only publishable rows leave, every edge carries a source, attributions
are emitted, freshness is stamped. Fails loudly on violations.

Writes export/atlas.json (canonical, committed) and mirrors it into the Astro site
at cbam-site/notebook/src/data/atlas.json when that project exists.

Usage: py pipeline/export_atlas.py
"""
import datetime
import json
import shutil
import sqlite3
import sys
from common import ROOT, DB_PATH

EXPORT = ROOT / "export" / "atlas.json"
SITE_COPY = ROOT.parent / "cbam-site" / "notebook" / "src" / "data" / "atlas.json"

REL_PHRASE = {
    "linked_by_treaty": "linked by treaty with",
    "negotiating_link": "negotiating a link with",
    "modeled_on": "modeled on",
    "responds_to": "responds to",
    "replaces": "replaces",
}
STATUS_LABEL = {
    "under_consideration": "under consideration",
    "under_development": "under development",
    "enabled_not_established": "enabled, not established",
    "pilot_mandated": "pilot mandated",
    "pilot_operational": "pilot operational",
    "enacted_future_start": "enacted, applies later",
    "in_force": "in force",
    "suspended": "suspended",
    "abolished": "abolished",
}


def doc_url(row):
    doc_id, celex, source_url = row
    if source_url:
        return source_url
    if celex:
        base = celex
        if celex.startswith("0"):
            base = "3" + celex[1:].split("-")[0]
        return f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{base}"
    return None


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    today = datetime.date.today()
    violations = []

    instruments = []
    for i in con.execute("SELECT * FROM instruments WHERE publishable=1 ORDER BY jurisdiction, id"):
        if not i["status_source"] or not i["last_checked"]:
            violations.append(f"{i['id']}: publishable without status_source/last_checked")
            continue
        age = (today - datetime.date.fromisoformat(i["last_checked"])).days
        docs = []
        for d in con.execute(
                "SELECT dc.role AS mrole, d.id, d.title, d.role AS drole, d.celex, "
                "d.source_url, d.metadata_only, d.status AS dstatus "
                "FROM doc_instrument dc JOIN documents d ON d.id = dc.doc_id "
                "WHERE dc.instrument_id=? ORDER BY dc.role, d.id", (i["id"],)):
            entry = {
                "id": d["id"],
                "label": d["title"] or d["drole"] or d["id"],
                "role": d["mrole"],
                "deep_layer": not d["metadata_only"],
                "status": d["dstatus"],
                "url": doc_url((d["id"], d["celex"], d["source_url"])),
            }
            if d["mrole"] == "legal_basis":
                for key, rel in (("amendments", "amends"), ("corrigenda", "corrects")):
                    entry[key] = con.execute(
                        "SELECT COUNT(*) FROM edges WHERE to_doc=? AND rel_type=?",
                        (d["id"], rel)).fetchone()[0]
                entry["pending_proposals"] = [
                    r[0] for r in con.execute(
                        "SELECT raw FROM edges WHERE to_doc=? AND rel_type='proposes_to_amend'",
                        (d["id"],))]
            docs.append(entry)
        edges = []
        for e in con.execute(
                "SELECT * FROM instrument_edges WHERE (from_id=? OR to_id=?) AND publishable=1",
                (i["id"], i["id"])):
            if not e["source"]:
                violations.append(f"edge {e['from_id']}->{e['to_id']}: publishable without source")
                continue
            outward = e["from_id"] == i["id"]
            other = e["to_id"] if outward else e["from_id"]
            other_name = con.execute("SELECT name_en FROM instruments WHERE id=?",
                                     (other,)).fetchone()
            phrase = REL_PHRASE[e["rel_type"]]
            if not outward and e["rel_type"] in ("modeled_on", "responds_to", "replaces"):
                phrase = {"modeled_on": "model for", "responds_to": "responded to by",
                          "replaces": "replaced by"}[e["rel_type"]]
            edges.append({"phrase": phrase, "other": other,
                          "other_name": other_name[0] if other_name else other,
                          "note": e["note"], "source": e["source"]})
        basis = None
        if i["status_basis_doc"]:
            basis = {"doc": i["status_basis_doc"], "unit": i["status_basis_unit"]}
        instruments.append({
            "id": i["id"], "name": i["name_en"], "name_local": i["name_local"],
            "jurisdiction": i["jurisdiction"], "type": i["instrument_type"],
            "status": i["status"], "status_label": STATUS_LABEL[i["status"]],
            "as_of": i["last_checked"], "stale": age > 180,
            "status_basis": basis, "notes": i["notes"],
            "unverified": json.loads(i["unverified"] or "[]"),
            "documents": docs, "edges": edges,
            "curated": i["status_source"] not in ("src-wb-cpd",),
        })

    sources = {r["id"]: dict(r) for r in con.execute("SELECT * FROM sources")}
    out = {
        "generated": today.isoformat(),
        "counts": {"instruments": len(instruments),
                   "jurisdictions": len({x['jurisdiction'] for x in instruments})},
        "attributions": [
            "Contains data from the World Bank Carbon Pricing Dashboard, "
            "licensed CC BY 4.0.",
            "EU legal metadata and texts: EUR-Lex / EU Publications Office. "
            "UK legislation: legislation.gov.uk. Turkish legislation: mevzuat.gov.tr.",
        ],
        "sources": {k: {"ref": v["ref"], "license": v["license"]} for k, v in sources.items()},
        "instruments": instruments,
    }
    if violations:
        print("EXPORT BLOCKED:")
        for v in violations:
            print(" ", v)
        sys.exit(1)
    EXPORT.parent.mkdir(exist_ok=True)
    EXPORT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(instruments)} instruments -> {EXPORT}")
    if SITE_COPY.parent.parent.exists():
        SITE_COPY.parent.mkdir(exist_ok=True)
        shutil.copyfile(EXPORT, SITE_COPY)
        print(f"mirrored -> {SITE_COPY}")


if __name__ == "__main__":
    main()
