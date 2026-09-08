# Document Index

Generated 2026-09-08 by build_db.py. Every tracked document and instrument. The database (db/regmap.db) is derived; rebuild with `py pipeline/build_db.py`.

## Instruments

| id | name | jurisdiction | type | status |
|---|---|---|---|---|
| eu-cbam | EU Carbon Border Adjustment Mechanism | EU | border_mechanism | in_force |
| eu-ets | EU Emissions Trading System | EU | ets | in_force |
| tr-ets | Turkey Emissions Trading System | TR | ets | pilot_mandated |
| tr-skdm | Turkey Border Carbon Regulation Mechanism (SKDM) | TR | border_mechanism | enabled_not_established |

## Documents — EU

| id | regime | type | status | role | units | notes |
|---|---|---|---|---|---|---|
| eu-2023-956 | CBAM | regulation | in_force | CBAM basic act (consolidated, incl. Omnibus 2025/2083) | 47 |  |
| eu-2025-2551 | CBAM | delegated_regulation | in_force | Verifier accreditation + verification process rulebook | 29 |  |
| eu-2025-2546 | CBAM | implementing_regulation | in_force | Verification specifics + report template | 9 |  |
| eu-2025-2547 | CBAM | implementing_regulation | in_force | Monitoring and reporting for the definitive period (the CBAM MRR) | 22 |  |
| eu-2025-2620 | CBAM | implementing_regulation | in_force | Benchmarks + free-allocation adjustment | 7 |  |
| eu-2025-2621 | CBAM | implementing_regulation | in_force | Default values (very large; tables) | 7 | large_document |
| eu-2024-2620 | CBAM | delegated_regulation | in_force | Permanently chemically bound CO2 - eligible products list | 7 |  |
| eu-2018-2066 | ETS | implementing_regulation | in_force | MRR - monitoring and reporting (consolidated) | 125 |  |
| eu-2018-2067 | ETS | implementing_regulation | in_force | AVR - accreditation and verification (consolidated, incl. ETS2 Ch IIIa) | 117 |  |
| eu-2003-87 | ETS | directive | in_force | ETS Directive (consolidated) | 82 |  |
| eu-2019-331 | ETS | delegated_regulation | in_force | FAR - free allocation rules (consolidated) | 41 |  |
| eu-2019-1842 | ETS | implementing_regulation | in_force | ALCR - activity level changes (consolidated) | 16 |  |
| eu-2023-1773 | CBAM | implementing_regulation | superseded | Transitional-period reporting rules (superseded for definitive period by 2025/2547) | 50 |  |

## Documents — TR

| id | regime | type | status | role | units | notes |
|---|---|---|---|---|---|---|
| tr-7552 | ETS | statute | in_force | Iklim Kanunu (Climate Law no. 7552) - legal basis for the Turkish ETS and SKDM | 21 | non_eurlex |

## Curated document relations

- **eu-2025-2547** supersedes **eu-2023-1773** — Definitive-period monitoring rules replace transitional Reg 2023/1773. Do not cite 1773 for monitoring-plan content.
