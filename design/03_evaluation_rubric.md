# Design Deliverable 3 — Evaluation rubric

What must be true before anything renders on the public atlas. Criteria are falsifiable; each
names its severity and its enforcement point. BLOCKING = export refuses; MATERIAL = export
warns, publish gate decides; ADVISORY = listed in the export report.

| # | criterion | severity | enforced |
|---|---|---|---|
| R1 | An instrument-to-instrument edge renders only with a non-null `source` | BLOCKING | CHECK constraint + export filter |
| R2 | A status renders only with `status_source` and a visible as-of date; a directory value never overrides a finer primary-sourced status — on conflict, primary wins and the discrepancy is listed in the export report | BLOCKING / MATERIAL (conflict) | CHECK + export diff |
| R3 | No empty shells: an instrument page needs ≥1 document row or an explicit "no primary document located" marker (`unverified` entry) | MATERIAL | export validator |
| R4 | Every rendered data value traces to a source whose license allows republication (`cc-by-4.0`, `public-law`, `manual`); `copyright-linkout` sources appear only as links. Required attributions (World Bank CC-BY line, the CCLW citation string) are present in the export's `attributions[]` | BLOCKING | export validator |
| R5 | Document ids are normalized: corrigenda attached to parents, consolidated ids carry version dates, non-legislation sectors filtered per the schema's sector rule | MATERIAL | parser tests |
| R6 | Freshness: `last_checked` older than 180 days renders a stale marker; older than 365 days demotes the instrument to MATERIAL in the export report. Every rendered source is covered by a watch channel | MATERIAL | export validator + watch coverage check |
| R7 | Counts reconcile: documents dropped during harvest (celex-less works, filtered sectors) are counted and reported, never silently discarded | MATERIAL | harvest log assertions |
| R8 | Site copy rules hold: no explanatory boilerplate, first person singular where voice appears, no reserved claims (accredited / "I verify" / verification opinion) anywhere in atlas copy | BLOCKING | publish-gate review (human) |
| R9 | Every page renders the generation date and the two-layer distinction is visible: deep-layer documents link to text, metadata-only documents visibly do not | ADVISORY | template review |

Pass threshold for first publish: zero BLOCKING, MATERIAL items individually accepted by Egg at
the publish gate, ADVISORY listed.

## End notes — what producing this surfaced
1. R2's conflict clause turned out to be the rubric's real content: two sources will disagree
   about status (a directory lags a gazette), and "which wins" had to be decided here, not in
   code review. Primary text wins; the disagreement itself is information and gets reported.
2. R7 exists because the CELLAR inventory showed 3–44 celex-less works per relation — the
   harvest will drop rows, and dropping must be an accounted-for act.
3. R6's "every rendered source has a watch channel" closes the loop with the stale-public-map
   risk: freshness is enforceable only if watching is a precondition of rendering.
