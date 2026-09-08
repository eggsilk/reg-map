# Design Deliverable 4 — Failure modes catalog

Per mode: detection and fallback. Grounded in observed behavior (2026-09-03 build,
2026-09-08 research and the live EUR-Lex block).

| # | failure | detection | fallback |
|---|---|---|---|
| F1 | Source answers a bot-block as an empty 200/202 (OBSERVED: EUR-Lex 2026-09-08) | `guarded_fetch` raises on tiny bodies (regression-tested) | channel reports error; content fetch falls back to CELLAR REST or a local run; findings never silently zero |
| F2 | Directory schema drift (WB XLSX columns renamed/moved) | harvest pins a column contract; unknown/missing columns fail the run | keep last-good snapshot in corpus; watcher marks directory stale; manual re-pin |
| F3 | Celex-less works in relation results (OBSERVED: 3–44 per relation) | resolver counts drops; R7 assertion | drop from render, log count; investigate only if ratio jumps |
| F4 | Celex shape surprises: corrigenda `R(nn)`, consolidated date-suffix, accession slashes (OBSERVED) | parser unit tests per shape | corrigenda→parent badges; accession dropped v1; unknown shapes quarantined to report |
| F5 | Wrong status from coarse directory mapping (WB 3-state vs our 8-state) | R2 conflict diff between directory and primary-sourced statuses | primary wins; discrepancy line in export report; manual override field |
| F6 | License terms change under us (CCLW commercial carve-out; WB terms page ambiguity) | annual license re-check task in the watcher's seen-list; the pending CCLW email | source flips to `copyright-linkout`; affected values leave the export at next build (R4) |
| F7 | Instrument identity churn: a slug renamed or two instruments merged after publish | slug registry file; export validator refuses id disappearance | redirects only, never renames; merges keep both ids, one canonical |
| F8 | Stale public artifact (map published, upkeep lapses) | R6 freshness demotions; Actions runs are the heartbeat — a failing scheduled run is itself an alert in the repo | page renders generation date; if watch dies >30 days, publish gate rule: take the atlas down rather than serve it stale (Egg's call at the time) |
| F9 | EU harvest over-expansion (955 citing works on the ETS Directive alone — OBSERVED) | expansion bounded: relations harvested only for documents that are members of a tracked instrument; citation edges depth-1 | no recursive expansion; new instruments enter via curation, not via graph walk |
| F10 | Resmî Gazete / mevzuat fetch rot (OBSERVED: SSL + JS shell) | guarded_fetch errors; TR corpus flagged non-automated | manual curl path documented in project memory; TR docs are few |
| F11 | GitHub Actions IP blocked by a source | same as F1 — errors in the committed watch report | split channels: SPARQL-based checks (CELLAR tolerates machines) run in Actions; web-scrape channels can run locally on demand |
| F12 | Two sources give conflicting document lineage (directory legal-basis link vs CELLAR relation) | export diff when both exist for the same instrument | CELLAR wins for EU; elsewhere the primary register wins; conflict reported |

## End notes — what producing this surfaced
1. F8 forced the ugliest and most useful sentence in the design: a dead atlas comes DOWN.
   Committing to that now makes the maintenance promise honest and bounded.
2. F9's bound ("relations only for member documents of tracked instruments") is the single
   rule that keeps the EU harvest from becoming a crawl of all EU law — worth stating as the
   harvest's invariant, not a tuning parameter.
3. F11 splits the watcher architecturally: machine-tolerant channels (SPARQL) belong in CI;
   fragile web channels degrade to local runs without taking the loop down.
