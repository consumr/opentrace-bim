# OpenTrace BIM v0.44.0

This release contains the complete OpenTrace BIM extension for IngeTrazo, provided as `OpenTrace_BIM-v0.44.0.zip`.

## Updates

- Restore the Home **Check for updates** button, wired to the real `UpdateManager`.
- Restore the optional automatic startup check, with user preference saved through `QSettings`.
- Show progress and status messages in Home during update discovery and installation.
- Look up future versions **directly on this repository's GitHub Releases feed**, without using the separate IngeTrazo extension catalogue.
- Validate update ZIP provenance, layout, versions, Python syntax and GitHub asset SHA-256 digest before installation.
- Preserve local files, back up existing plugin state and attempt rollback on installation failure.

## Compatibility and first migration

**Important:** installations already running v0.12.9 check the IngeTrazo catalogue (which still lists v0.12.9); they **will not** find v0.44.0 from their old button until the catalogue is updated. Existing users can install this ZIP manually once, then use the GitHub-direct update button for subsequent releases. The catalogue is not required by the *new* updater.

## Verification

The v0.44.0 ZIP asset has **SHA-256** `b03455f4c24b95592e4ce671bdb85eb60e06bff02a617bcc497d8697fa40a937`.
The complete package and manifest were validated locally. 100 existing regression tests plus 10 updater-specific tests passed, and 126 Python modules compiled. Runtime GUI acceptance in IngeTrazo on Windows is still pending for this specific update.

**Source code:** the `v0.44.0` Git tag and `main/OpenTrace_BIM/` should reflect exactly the same files as the ZIP in this release.
