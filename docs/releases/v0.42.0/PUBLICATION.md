# v0.42.0 — Publication runbook and responsibilities

**Repository:** `lelopes05/opentrace-bim`. **Current main at creation of preparation branch:** `bf57de535bbfa85e8c7abdfc7b3d195241c3ed87` (2026-10-09). **Branch:** `release/0.42.0-prep`. **Release status:** maintainer-tested and approved v0.42.0 Alpha. No RC designation needed.

This branch adds **documentation only** until the actual plugin code is integrated. Do **not** tag its old-code HEAD as v0.42.0.

1. Bring complete `OpenTrace_BIM/` folder from `OpenTrace_BIM-v0.42.0-PLUGIN-CANDIDATE.zip` into the release branch, reviewing the full diff. Preserve the GPL license and all non-overlapping source files.
2. Review whether `arquitetura_parametrica/` is still an installed extension in this repo; do not accidentally enable two separate extension copies.
3. Confirm the internal candidate version is `0.42.0` and commit complete contents and tests.
4. Compare real GitHub tree with previous release/base; the experimental ZIP reports are not equivalent to a GitHub diff.
5. Retain the maintainer's in-host acceptance statement and run further automated/Windows regression checks as appropriate. The detailed checklist is for tracking future edge cases, not to reverse approval already given.
6. Merge reviewed PR into `main` only after source integration; create tag `v0.42.0` **on the merged source commit**, not on old code. This is an official v0.42.0 Alpha release; GitHub prerelease status is optional and not required by the Alpha lifecycle.
7. Create GitHub Release with title `OpenTrace BIM v0.42.0`, tag `v0.42.0`, and copy [RELEASE_NOTES.md](RELEASE_NOTES.md). Do not mark as a GitHub prerelease merely due to ongoing Alpha development.
8. Attach installable ZIP plus the dossier ZIP and publish SHA-256 hashes from [SOURCE_PROVENANCE.md](SOURCE_PROVENANCE.md).
9. Separately consider the IngeTrazo update catalog `ingelibre/ingetrazo-extensions/main/catalog.json`; GitHub publication does not update the catalog and it must not point users to unaccepted prerelease by accident.
10. Verify release link, ZIP download, checksum, clean Windows install, rollback and hosted BIM sample.

**Platform limitation in this session:** available connected GitHub actions can commit code, create branches and PRs/tags but do not expose create-Release/attach-asset. ZIP attachment must be performed in GitHub UI or another authenticated API environment. This does not prevent committing supporting docs.
