# OpenTrace BIM v0.42.0 — Release preparation

**Status:** release candidate (not yet Windows/IngeTrazo accepted). **Prepared:** 2026-10-16. **Target:** IngeTrazo 0.5.7+.

This directory records the source-provenance, consolidated features, tests, release notes and open risks of the *local* v0.42.0 candidate. The GitHub code in `main` is still an earlier version unless and until the candidate source is integrated and reviewed. Do not create a final v0.42.0 tag on old code.

## Distribution artifacts to attach manually to the GitHub Release

- `OpenTrace_BIM-v0.42.0-PLUGIN-CANDIDATE.zip` — complete installable `OpenTrace_BIM/` plugin folder; SHA-256: `cad7ea3b819f6add7f35c00046ab37d60e80b2bf93af680c87aa0ce60febae4c`
- `OpenTrace_BIM-v0.42.0-RELEASE-DOSSIER.zip` — source, inherited reports, tests, evidence and release documentation; SHA-256: `2cc15b81457a37d3aa6c1387451b38f51bf681fd38560a834e62d30d2101616a`

Both archives were verified locally. Neither archive is attached to GitHub merely by the presence of these notes.

## Important precedence of late fixes

- The latest checkbox correction supersedes earlier reports: side-stile and upper/lower-rail checkboxes are **initially checked for new panel/glass presets but can be toggled independently**. This also means the user can remove physically necessary supports.
- For wall edge finishes, the four selectors require their own **Apply** below the controls. Wall body/layer material changes remain immediate.
- The former Composite dialog is now **Material Composer**.
- Historical files referring to 0.12.9 describe older work, not the candidate release number.

## Publication gate

1. Integrate the complete candidate source in a release branch, retaining GPL-3.0-or-later and avoiding two active extension folders.
2. Review the pull request, compare against `main`, and run automated checks.
3. Validate critical GUI, `.igz` persistence and IFC round-trips on Windows.
4. Until accepted, publish only as GitHub **Pre-release**, not stable; attach the ZIP and its SHA-256; check correct internal version `0.42.0`.
5. Update the external IngeTrazo extension catalog separately and only after acceptance; this GitHub work does not update that catalog.

See [CHANGELOG.md](CHANGELOG.md), [KNOWN_ISSUES.md](KNOWN_ISSUES.md), [QA_WINDOWS.md](QA_WINDOWS.md), [SOURCE_PROVENANCE.md](SOURCE_PROVENANCE.md), [RELEASE_NOTES.md](RELEASE_NOTES.md) and [PUBLICATION.md](PUBLICATION.md).
