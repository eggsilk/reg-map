"""Watch for regulatory change. Three checks, each independent; failures are reported, not fatal.

  1. EU consolidation check - for each tracked act, does EUR-Lex list a newer
     consolidated version than the one in our manifest?
  2. EU new-act discovery - CELLAR SPARQL: works citing the CBAM basic act or the
     ETS Directive that we do not track yet.
  3. TR gazette scan - today's Resmi Gazete index, keyword-matched.

Writes watch_report.json and prints a human summary. Exit 0 = ran; findings are data, not errors.

Usage: py pipeline/watch.py
"""
import datetime
import json
import re
import urllib.parse
import urllib.request
from common import ROOT, EURLEX_OVERVIEW, load_manifest, fetch_url, UA

REPORT = ROOT / "watch_report.json"
SEEN = ROOT / "watch_seen.json"
SPARQL = "https://publications.europa.eu/webapi/rdf/sparql"
TR_KEYWORDS = ["iklim", "emisyon", "karbon", "SKDM", "sera gaz"]
WATCH_BASES = ["32023R0956", "32003L0087"]  # new acts must cite one of these


def base_celex(celex):
    """Consolidated id 02023R0956-20251020 -> base 32023R0956."""
    m = re.match(r"0(\d{4}[RLD]\d{4})", celex)
    return f"3{m.group(1)}" if m else celex


def check_consolidations(man):
    findings, errors = [], []
    for doc in man["documents"]:
        celex = doc.get("celex")
        if not celex:
            continue
        current = re.search(r"-(\d{8})$", celex)
        try:
            page = fetch_url(EURLEX_OVERVIEW.format(celex=base_celex(celex)))
        except Exception as e:
            errors.append(f"{doc['id']}: overview fetch failed ({type(e).__name__})")
            continue
        versions = sorted(set(re.findall(r"0\d{4}[RLD]\d{4}-(\d{8})", page)))
        if not versions:
            continue
        latest = versions[-1]
        if current is None or latest > current.group(1):
            findings.append({"type": "new_consolidation", "doc": doc["id"],
                             "have": current.group(1) if current else "(base act)",
                             "latest": latest})
    return findings, errors


def check_new_acts(man):
    tracked = {base_celex(d["celex"]) for d in man["documents"] if d.get("celex")}
    findings, errors = [], []
    for base in WATCH_BASES:
        q = f"""PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?celex WHERE {{
  ?target cdm:resource_legal_id_celex '{base}'^^<http://www.w3.org/2001/XMLSchema#string> .
  ?w cdm:work_cites_work ?target .
  ?w cdm:resource_legal_id_celex ?celex .
}} LIMIT 500"""
        url = SPARQL + "?" + urllib.parse.urlencode({"query": q, "format": "application/json"})
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read().decode("utf-8"))
            for b in data["results"]["bindings"]:
                celex = b["celex"]["value"]
                if re.match(r"3\d{4}[RLD]\d{4}$", celex) and celex not in tracked:
                    findings.append({"type": "untracked_citing_act", "celex": celex,
                                     "cites": base})
        except Exception as e:
            errors.append(f"SPARQL {base}: {type(e).__name__}: {e}")
    # dedupe
    seen, out = set(), []
    for f in findings:
        if f["celex"] not in seen:
            seen.add(f["celex"])
            out.append(f)
    return out, errors


def check_tr_gazette():
    findings, errors = [], []
    today = datetime.date.today()
    url = f"https://www.resmigazete.gov.tr/{today.strftime('%d.%m.%Y')}"
    try:
        page = fetch_url(url)
    except Exception as e:
        return findings, [f"resmigazete: {type(e).__name__}: {e}"]
    text = re.sub(r"<[^>]+>", " ", page)
    for kw in TR_KEYWORDS:
        for m in re.finditer(kw, text, re.I):
            ctx = re.sub(r"\s+", " ", text[max(0, m.start() - 120):m.end() + 120]).strip()
            findings.append({"type": "tr_gazette_hit", "keyword": kw, "date": str(today),
                             "context": ctx})
    return findings[:20], errors


def finding_key(f):
    return json.dumps({k: f[k] for k in sorted(f) if k not in ("date", "context")},
                      sort_keys=True)


def main():
    man = load_manifest()
    seen = set(json.loads(SEEN.read_text(encoding="utf-8"))) if SEEN.exists() else set()
    all_findings, all_errors = [], []
    for name, fn in [("consolidations", lambda: check_consolidations(man)),
                     ("new_acts", lambda: check_new_acts(man)),
                     ("tr_gazette", lambda: check_tr_gazette())]:
        f, e = fn()
        all_findings += f
        all_errors += [f"[{name}] {x}" for x in e]
        print(f"{name}: {len(f)} finding(s), {len(e)} error(s)")
    new = [f for f in all_findings if finding_key(f) not in seen]
    seen.update(finding_key(f) for f in all_findings)
    SEEN.write_text(json.dumps(sorted(seen), indent=1), encoding="utf-8")
    report = {"run": datetime.datetime.now().isoformat(timespec="seconds"),
              "new_findings": new, "total_findings": len(all_findings),
              "errors": all_errors}
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(new)} NEW finding(s) ({len(all_findings)} total) -> watch_report.json")
    for f in new[:15]:
        print(" ", f)
    if all_errors:
        print("errors:")
        for e in all_errors:
            print(" ", e)


if __name__ == "__main__":
    main()
