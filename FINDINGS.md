# Findings

Things discovered while building and running reg-map. Dated, succinct, checkable.
Source material for the eventual site write-up; not itself site copy.

## About the regime

- **A drafting error, live in force (2026-09-01).** IR 2025/2546 Art. 2 cites "Section 2.12 of
  Annex II" to DR 2025/2551 for physical site visits — 2.12 is Sampling; the site-visit substance
  is 2.13. No corrigendum yet as of 2026-09-08 (the act shows 4 corrigenda, none on this).
- **The default-values act could not sit still (2026-09-03 / 2026-09-08).** IR 2025/2621
  (adopted Dec 2025) was amended effective 01.01.2026 — and then had Annexes I and IV, the
  default-value tables themselves, corrected by IR 2026/1740 in July. Two revisions in eight
  months to the numbers importers fall back on. The watcher found the first; the relation
  harvest found the second.
- **CO₂ bound in urea is not deductible (2026-08-20, confirmed in corpus 2026-09-01).**
  DR 2024/2620's annex lists only mineral carbonates in construction products as permanently
  bound. Widely circulated training material teaches the opposite for urea.
- **The CBAM secondary-legislation tree is bigger than practitioners track (2026-09-08).** One
  metadata query returned 15 acts based on Reg. 2023/956 — including a correcting act of
  20 July 2026 (IR 2026/1740) we had never seen, plus registry, sales, and certificate-price
  acts. Two Commission proposals to amend the basic act are pending.
- **The ETS Directive is a 20-year palimpsest (2026-09-08).** 17 amending acts 2004–2024,
  955 works citing it, 139 acts using it as legal basis — all machine-readable.
- **Turkey's climate law encodes two statuses most maps flatten (2026-09-01).** The ETS is
  *mandated with a pilot phase* (Geçici Madde 1); the border mechanism (SKDM) is only *enabled* —
  "may be established", procedures assigned to the Trade Ministry (Madde 8). Neither is
  "in force" nor merely "planned".

## About the data landscape

- **No directory on earth lists border mechanisms (2026-09-08).** The World Bank dashboard
  covers taxes and ETSs; ICAP is ETS-only. EU CBAM, UK CBAM and Turkey's SKDM must be curated
  by hand from primary law.
- **There is no "implements" relation in EU legal metadata (2026-09-08).** The implements-tree
  is reconstructed from `based_on` (incoming) plus `completes` (delegated acts). Everyone's
  mental model has an arrow the data does not.
- **EUR-Lex blocks robots; the EU's own machine door does not (2026-09-08).** The website
  answers scripted fetches with HTTP 202 and an empty body; the publications office SPARQL
  endpoint answered the same queries in under half a second, no key required.
- **Primary text beats directories on freshness and precision (2026-09-08).** The World Bank
  lists Türkiye's ETS as "under development"; the statute mandates a pilot. Both are honest at
  their own resolution — a map has to let the finer source win and report the gap.
- **Licensing is a three-way split (2026-09-08).** World Bank data: CC-BY 4.0, republishable.
  Climate Change Laws of the World: CC-BY. ICAP: plain copyright — link, never copy.
- **CELEX ids come in three surprise shapes.** Corrigenda (`...R(01)`), consolidated snapshots
  (`0...-YYYYMMDD` — the date IS the version), accession acts with slashes. And some relation
  results have no CELEX at all (3–44 per query) — every harvest must count what it drops.
- **The operational layer is invisible to legal metadata (2026-09-03).** The Commission's
  verifier guidance (Aug 2026) and operator guidance series live on Commission web pages that
  EUR-Lex never sees. Watching law alone misses the documents practitioners actually use.

## About building self-updating systems

- **A blocked source must fail loudly (2026-09-08).** Bot mitigation that returns empty 200s
  turns a watcher silently blind. "No findings" and "could not look" are different results.
- **Directories move; search indexes remember the old address (2026-09-08).** The research
  agent's download URL for the WB data was stale (found via search, never fetched). The live
  link — a newer edition — took opening the actual site in a browser.
- **Corporate firewalls fingerprint clients (2026-09-08).** The World Bank's WAF rejects
  Python's urllib but accepts curl, same headers. The EUR-Lex block and this one argue for
  never assuming one fetch path.
- **Windows default encoding is a standing hazard (2026-09-08).** cp1252 decoding broke both a
  JSON read and a subprocess pipe (one UTF-8 byte killed the reader thread, stdout came back
  None). Every read and every pipe gets an explicit encoding now; both bugs are regression-tested.
- **Count drift is a bug siren (2026-09-08).** A rebuild's document count came out 2 higher than
  arithmetic predicted; chasing it exposed duplicate rows from joining on CELEX strings instead
  of act identity (a consolidated id doesn't contain its base id). When derived numbers don't
  reconcile, the pipeline is wrong somewhere — never shrug at a delta.
- **The gazette watcher saw real news on day one (2026-09-08).** Turkey's ratification
  decisions with the UNFCCC Secretariat (COP31 hosting) appeared in that morning's Resmî
  Gazete scan.
