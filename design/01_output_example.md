# Design Deliverable 1 — Output by example

Hand-crafted atlas entry for one real instrument (Turkey ETS), written as the production system
would render it on egeipek.info. Every stated fact below is grounded in the corpus text we hold
(tr-7552, fetched 2026-09-01 from mevzuat.gov.tr) or explicitly marked pending/unverified.
Site register applies: benji.org system, facts only, no explanatory boilerplate.

---

## A. The page as rendered (content, not markup)

**Turkey — Emissions Trading System**
`tr-ets` · Türkiye · ETS · **pilot phase mandated, not yet operational** · as of 2026-09-07

- Legal basis: İklim Kanunu No. 7552 (Climate Law). Article 9 establishes the ETS under the
  Climate Change Presidency: allocation planning, emission permits, annual surrender obligation.
- Pilot phase: Transitional Article 1 — a pilot period precedes full operation; its scope,
  duration and procedures are delegated to secondary regulation.
- Implementing regulation (yönetmelik): not located. *unverified*

Documents
| id | title | role | status | text |
|---|---|---|---|---|
| tr-7552 | İklim Kanunu (No. 7552) | statute, legal basis | in force | in corpus, article-level |
| — | ETS pilot yönetmelik | implementing regulation | not located · *unverified* | — |

Relations
| edge | target | source |
|---|---|---|
| member of national framework | tr-climate-law-framework | Art. 9 |
| modeled on | eu-ets | *pending — directory factsheet required before this edge renders* |

Related instrument: **Turkey — SKDM (Border Carbon Regulation Mechanism)** `tr-skdm` —
**enabled, not established**: Article 8(1)(ç) provides the mechanism *may* be established;
reporting, scope and procedures assigned to the Ministry of Trade. Separate entry.

Provenance: statute text fetched 2026-09-01 from mevzuat.gov.tr (consolidated PDF). Directory
confirmations (ICAP, World Bank Carbon Pricing Dashboard): pending harvest. Last checked
2026-09-07.

---

## B. The record behind it (target data shape, pre-schema)

```json
{
  "id": "tr-ets",
  "kind": "instrument",
  "name_en": "Turkey Emissions Trading System",
  "name_local": "Emisyon Ticaret Sistemi (ETS)",
  "jurisdiction": "TR",
  "instrument_type": "ets",
  "status": "pilot_mandated",
  "status_basis": {"doc": "tr-7552", "unit": "Geçici Madde 1"},
  "documents": [
    {"doc": "tr-7552", "role": "legal_basis", "deep_layer": true},
    {"doc": null, "role": "implementing_regulation", "note": "not located", "unverified": true}
  ],
  "edges": [
    {"rel": "modeled_on", "to": "eu-ets", "source": null, "publishable": false}
  ],
  "sources": [
    {"kind": "primary_text", "ref": "mevzuat.gov.tr", "fetched": "2026-09-01"},
    {"kind": "directory", "ref": "icap", "fetched": null, "pending": true}
  ],
  "last_checked": "2026-09-07",
  "unverified": ["implementing yönetmekik status", "pilot start date"]
}
```

---

## End notes — what producing this surfaced

1. **The status vocabulary needs more states than in-force/superseded.** SKDM is *enabled, not
   established* (a "may be established" clause); the ETS is *pilot mandated, not yet operational*.
   Enabling clauses and mandated-but-unstarted regimes are common worldwide; the schema needs a
   status enum that carries legal-mandate strength, with the citing unit as `status_basis`.
2. **An edge without a citable source must not render publicly.** "Modeled on EU ETS" is our own
   inference until a directory factsheet or the law itself backs it. The record keeps the edge
   with `publishable: false`; the page shows it as pending or not at all. This becomes the
   rubric's first hard criterion.
3. **Instruments and documents are many-to-many.** One statute (7552) grounds two instruments
   (ETS, SKDM). Membership edges, not ownership.
4. **The two layers join naturally.** tr-7552 exists in the deep layer with article-level units,
   so `status_basis` can point at "Geçici Madde 1" as a real unit and the page can link into the
   text. Atlas documents carry a `deep_layer` flag.
5. **Absence is content.** The not-yet-located yönetmelik gets a row with an unverified marker,
   not silence — same convention as the site's `unverified` frontmatter field.
6. **Local-language names are first-class** (name_en + name_local), and "as of" dates render
   visibly on the page, not only in the record.
