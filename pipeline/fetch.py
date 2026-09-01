"""Fetch tracked documents into the corpus.

Usage:
    py pipeline/fetch.py            # fetch everything missing
    py pipeline/fetch.py --id X     # fetch one document by manifest id
    py pipeline/fetch.py --refresh  # re-fetch everything
"""
import argparse
import datetime
import json
import sys
from common import (ROOT, EURLEX_HTML, load_manifest, doc_paths, fetch_url,
                    strip_html)

FETCH_LOG = ROOT / "corpus" / "fetch_log.json"


def fetch_doc(doc):
    html_path, txt_path = doc_paths(doc)
    if "celex" in doc:
        lang = doc.get("language", "en").upper()
        url = EURLEX_HTML.format(lang=lang, celex=doc["celex"])
    elif "source_url" in doc:
        url = doc["source_url"]
    else:
        return {"id": doc["id"], "ok": False, "error": "no celex or source_url"}
    try:
        raw = fetch_url(url)
    except Exception as e:
        return {"id": doc["id"], "ok": False, "error": f"{type(e).__name__}: {e}", "url": url}
    # EUR-Lex serves an error page with 200 sometimes; sanity-check size/content
    if "celex" in doc and len(raw) < 5000:
        return {"id": doc["id"], "ok": False,
                "error": f"suspiciously small response ({len(raw)} bytes) - likely not the document",
                "url": url}
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(raw, encoding="utf-8")
    txt_path.write_text(strip_html(raw), encoding="utf-8")
    return {"id": doc["id"], "ok": True, "bytes": len(raw), "url": url,
            "fetched_at": datetime.date.today().isoformat()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    man = load_manifest()
    log = json.loads(FETCH_LOG.read_text(encoding="utf-8")) if FETCH_LOG.exists() else {}
    results = []
    for doc in man["documents"]:
        if args.id and doc["id"] != args.id:
            continue
        html_path, _ = doc_paths(doc)
        if html_path.exists() and not args.refresh and not args.id:
            continue
        res = fetch_doc(doc)
        results.append(res)
        status = "OK " if res["ok"] else "FAIL"
        extra = f"{res.get('bytes', 0):,} bytes" if res["ok"] else res["error"]
        print(f"{status} {doc['id']}: {extra}")
        if res["ok"]:
            log[doc["id"]] = res
    FETCH_LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")
    fails = [r for r in results if not r["ok"]]
    print(f"\n{len(results) - len(fails)} fetched, {len(fails)} failed.")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
