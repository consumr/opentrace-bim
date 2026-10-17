# v0.42.0 — Origin, hashes and validation limits

- **User-selected release number:** `0.42.0`.
- **Immutable received source:** `OpenTrace_BIM-EXPERIMENTAL-ISOLADO-FIX-CHECKBOX-INTERATIVOS-20261016(1).zip`.
- **Source SHA-256:** `9f55a7b886842339b71d65ae07410c5f9e4ebf790d17b65d3db3ebb35c7baf05`.
- Received archive had 208 entries; 207 files recorded and validated by original manifest; original declared internal plugin version `0.12.9`.
- Candidate internal `OpenTrace_BIM/__init__.py` declares `__version__ = "0.42.0"`.
- Candidate ZIP SHA-256: `cad7ea3b819f6add7f35c00046ab37d60e80b2bf93af680c87aa0ce60febae4c`.
- Full documentation dossier ZIP SHA-256: `2cc15b81457a37d3aa6c1387451b38f51bf681fd38560a834e62d30d2101616a`.

## Development ancestry

1. Walls/materials/IFC base from experimental Apply-Edges/Material-Composer package, 2026-10-16.
2. V9.1 door code/editor selectively merged from isolated local door package on 2026-10-16; local merge report documented 13 altered + 3 added modules at that step.
3. Subsequent door editor English/grooves/isometric preview corrections.
4. Final frame-checkbox interaction correction superseding previous intentional disabled-state report.
5. Packaging into v0.42.0 changed version metadata, install instructions and release notes, **not new motor logic**.

## Reported automated validation

- 100 base tests OK, 71 door/editor tests OK, 3 merge integration tests OK, 12 focused door regressions OK (some overlap).
- Synthetic V7/V8 checks, 36 synthetic combinations, Python compile and integrity checks reported OK.
- PySide6 and IngeTrazo/Windows live GUI were unavailable **to the automated assistant environment**, but **the maintainer confirms in-host functional testing and approval of this version**. Individual external IFC interoperability, GPU configurations and legacy `.igz` compatibility combinations are not independently verified by the assistant.

**Not a historical diff:** this candidate's feature inventory must not be represented as a proven `v0.41.x→v0.42.0` commit-by-commit changelog. The official repository's latest publicly published release observed during preparation was v0.12.9, which does not establish all intervening project history.
