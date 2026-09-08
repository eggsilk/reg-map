# Design Deliverable 2 — Data model and ontology

Grounded in D1 (the Turkey ETS example) and the 2026-09-08 research results (directory licensing;
CELLAR relation inventory). Field-level contracts for the atlas layer; the existing deep layer
(documents/units/edges for full-text acts) is extended, not replaced.

## Entities

### instrument (new table)
| field | type | contract |
|---|---|---|
| id | TEXT PK | slug, e.g. `tr-ets`, `eu-cbam`. Public URL component — NEVER renamed once published (D4-F7). |
| name_en, name_local | TEXT | both required; name_local may equal name_en |
| jurisdiction | TEXT | ISO 3166-1 alpha-2, `EU`, or subnational `US-CA` style |
| instrument_type | TEXT | enum: `ets`, `carbon_tax`, `border_mechanism`, `hybrid` |
| status | TEXT | enum: `under_consideration`, `under_development`, `enabled_not_established`, `pilot_mandated`, `pilot_operational`, `in_force`, `suspended`, `abolished` |
| status_source | TEXT | source id that grounds the status (required for publish, R2) |
| status_basis_doc, status_basis_unit | TEXT | optional pointer into the deep layer ("tr-7552", "Geçici Madde 1") |
| last_checked | TEXT | ISO date, rendered visibly |
| publishable | INTEGER | 0/1; gates export |
| notes | TEXT | curator note, may render |

Status mapping from directories: World Bank's `Under consideration / Under development /
Implemented` map to `under_consideration / under_development / in_force`; the finer states
(`enabled_not_established`, `pilot_*`) come only from primary-text curation and always carry
`status_basis`. A directory value never overwrites a finer primary-sourced status (R2).

Scope: compliance instruments only. Crediting/offset mechanisms (the WB dataset's second
section) are excluded from v1.

### document (existing table, extended)
New columns: `title` TEXT, `date_document` TEXT, `metadata_only` INTEGER (1 = no corpus text —
the broad layer), `official_id` TEXT (CELEX for EU; national identifier elsewhere).
CELEX shapes handled: `3YYYYRNNNN`, consolidated `0YYYYRNNNN-YYYYMMDD`, corrigenda
`...R(nn)` (attach to parent, never standalone nodes), accession `1...` with slash (drop v1).
Sector filter: only sector-3 (legislation) and sector-0 (consolidated) render by default;
sector-5 proposals render only in the "pending changes" panel; sector-6 case law excluded v1.

### doc_instrument (new)
`doc_id`, `instrument_id`, `role` enum: `legal_basis`, `implementing_regulation`,
`delegated_regulation`, `amendment`, `guidance`, `transposition`. Many-to-many (D1 note 3).

### edges (existing table, extended)
New columns: `rel_type`, `source`, `retrieved`.
Document-to-document rel_type values and their CELLAR properties (verified 2026-09-08):
| rel_type | CDM property | render as |
|---|---|---|
| cites | work_cites_work | citation lists (deep layer keeps regex-extracted unit-level cites) |
| legal_basis | resource_legal_based_on_resource_legal | the implements-tree (incoming = secondary legislation) |
| amends | resource_legal_amends_resource_legal | amendment timeline (dated) |
| completes | resource_legal_completes_resource_legal | delegated acts, shown with implements-tree |
| corrects | resource_legal_corrects_resource_legal | corrigenda badges on the parent |
| consolidates | act_consolidated_consolidates_resource_legal | version timeline (date-suffixed celex = version date) |
| repeals | resource_legal_repeals_resource_legal (+implicit) | lifecycle |
| proposes_to_amend | resource_legal_proposes_to_amend_resource_legal | "pending changes" panel |
| supersedes | manual only | curated lifecycle notes |

### instrument_edges (new)
`from_id`, `to_id`, `rel_type` enum: `modeled_on`, `linked_by_treaty`, `responds_to`,
`replaces`; `source` TEXT (required to publish — R1), `note` TEXT, `publishable` INTEGER.
All cross-jurisdiction claims live here and are curated, never harvested.

### sources (new)
`id`, `kind` (`primary_text`, `cellar`, `directory`, `manual`), `ref` (URL or citation),
`license` (`cc-by-4.0`, `public-law`, `copyright-linkout`, `manual`), `fetched` date.
Allowed-to-republish licenses: `cc-by-4.0`, `public-law`, `manual` (with citation).
`copyright-linkout` sources (ICAP) may ground a LINK on a page, never a data value (R4).

## CHECK constraints (rubric backstops, per methodology)
- `instrument.status` IN the enum list.
- `instrument_edges`: `publishable = 1` requires `source IS NOT NULL`.
- `instrument`: `publishable = 1` requires `status_source IS NOT NULL AND last_checked IS NOT NULL`.
- `edges.rel_type` IN the enum list.

## Export contract (site-facing)
`export/atlas.json`: `{generated, attributions[], instruments[]}` where each instrument embeds
its documents (with roles), edges (publishable only), status block with as-of date, and
unverified[] markers. Per-instrument files optional later. The Astro site renders ONLY the
export; it never reads the DB.

## End notes — what producing this surfaced
1. The CELLAR inventory killed a guessed abstraction: there is no "implements" property —
   the implements-tree IS `based_on` (incoming) plus `completes`. Rel_type names in our schema
   are ours; the mapping table above is the contract with CELLAR.
2. Consolidation snapshots via SPARQL replace the overview-page scrape for the consolidation
   watch channel (decision D5-11) — also immune to the EUR-Lex web block observed 2026-09-08.
3. Directory verdicts collapse `sources.license` into four values; ICAP forced the
   link-only license class, which the schema now enforces rather than policy prose.
4. Corrigenda-as-badges (not nodes) and the sector filter both exist because the inventory
   showed heterogeneous citation sets — schema absorbs what would otherwise be display hacks.
