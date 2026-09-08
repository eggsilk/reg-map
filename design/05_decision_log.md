# Design Deliverable 5 — Decision log (append-only)

| # | date | decision | why | constrains |
|---|---|---|---|---|
| 1 | 2026-09-03 | Text corpus is source of truth; no PDF shelf; DB derived and gitignored | Egg: index of documents replaces the shelf; rebuildability | everything downstream rebuilds from corpus + manifest |
| 2 | 2026-09-03 | Private GitHub repo; watch loop in Actions | continuity + self-building | CI must run stdlib-only |
| 3 | 2026-09-07 | Two-layer model: deep text layer (EU+TR) + broad metadata-only atlas layer | text pulling doesn't scale worldwide; the map is the product | atlas features may not require text for new jurisdictions |
| 4 | 2026-09-07 | Directory-first discovery for the world layer | sponsorship-era lesson: harvest maintained directories, don't assemble | coverage inherits directory coverage; gaps curated by hand |
| 5 | 2026-09-07 | Two node types: instruments + documents, many-to-many membership | directories list regimes; one statute grounds two instruments (TR) | cross-border edges connect instruments only |
| 6 | 2026-09-07 | Public form = atlas pages + focused subgraphs, benji.org system; no global graph | hairballs demo badly; site copy rules | D3 only per-instrument; export is static JSON |
| 7 | 2026-09-07 | reg-map stays private; site consumes export | separates working instrument from public artifact | export contract is the only site-facing surface |
| 8 | 2026-09-08 | WB CPD harvested+republished (CC-BY 4.0, static XLSX); CCLW harvested+republished (CC-BY, citation string, send carve-out email); ICAP link-out only | licensing research, verified from terms pages | sources.license enum; R4 |
| 9 | 2026-09-08 | Border mechanisms (EU CBAM, UK CBAM, TR SKDM) are hand-curated entries | no directory covers them (verified); it's the practitioner-differentiating content | curation effort is a standing cost; also the atlas's headline |
| 10 | 2026-09-08 | Implements-tree = CELLAR `based_on` (incoming) + `completes`; no "implements" property exists | live inventory | rel_type mapping table in D2 is the contract |
| 11 | 2026-09-08 | Consolidation watch moves to SPARQL (`act_consolidated_consolidates`) off the EUR-Lex overview scrape | EUR-Lex web blocked us (202/empty) while CELLAR answered in 0.4 s; snapshots carry version dates in the celex | watch channel rewrite in phase 3; overview scrape becomes fallback |
| 12 | 2026-09-08 | Crediting/offset mechanisms excluded from v1 | scope discipline; WB carries them but they're a different regime kind | instrument_type enum omits them; revisit only on Egg's ask |
| 13 | 2026-09-08 | Harvest invariant: EU relations harvested only for documents that are members of a tracked instrument; no recursive graph walk | 955 citing works on the ETS Directive alone (observed) | new instruments enter via curation |
| 14 | 2026-09-08 | A dead atlas comes down: if the watch loop is dead >30 days, unpublish rather than serve stale | stale public map damages the trust the site exists to build | publish gate rule; Egg's call at the time |
| 15 | 2026-09-08 | Status vocabulary carries legal-mandate strength (8 states incl. `enabled_not_established`, `pilot_mandated`); finer states require `status_basis` in primary text | D1: Turkey's "may be established" SKDM clause would be flattened to wrongness by a 3-state enum | R2; directory values never override primary-sourced finer states |
| 16 | 2026-09-09 | Edge type `negotiating_link` added (Egg-approved) | WB documents the May 2025 UK-EU intention to link; asserting `linked_by_treaty` would be false, dropping it loses real information | instrument edge enum |
| 17 | 2026-09-09 | Status `enacted_future_start` added | UK CBAM: Finance Act 2026 Part 5 enacted, charges arise 1 Jan 2027 (verified from SI 2026/830) - a state the vocabulary lacked | status enum; UK entry |
| 18 | 2026-09-09 | Corpus promotion of the discovered CBAM secondary acts; 2024/2649 excluded (Swedish-language corrigendum only); watcher-found 2026/65 (anti-dumping) and 2026/667 (Climate Law target) ruled out of regime scope | title inspection | manifest tier A set |
