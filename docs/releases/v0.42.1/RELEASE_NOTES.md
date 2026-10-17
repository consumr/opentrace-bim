# OpenTrace BIM v0.42.1 — Alpha

Maintenance update for the already published v0.42.0 Alpha. The architectural modeling engine is unchanged; this patch improves distribution and updates.

## Fixes

- **Updater checks GitHub directly:** the button searches published OpenTrace BIM Releases in `lelopes05/opentrace-bim`, instead of relying on the IngeTrazo catalogue to announce every new release.
- **Integrity checks:** accept only versioned `OpenTrace_BIM-vX.Y.Z.zip` assets from this repository, with the release asset's SHA-256 digest, and verify the downloaded package's internal version and Python syntax before installing.
- **Installation cleanup:** parse the previous plugin's SHA-256 package manifest correctly when removing outdated, package-owned files.
- **Explicit install approval remains:** checking does not download/install automatically. The user chooses **Download and install** and restarts IngeTrazo.

## Compatibility

The **v0.42.1 updater** gains GitHub-direct discovery after installation. Previously installed versions (including v0.12.9 and v0.42.0) continue to consult IngeTrazo's separate catalogue; their existing code cannot be changed remotely by publishing a new GitHub release. They require **one catalogue-announced update** or a manual install to migrate. This is not solved by updating the repository alone.

## Release status

Alpha. The v0.42.0 feature set was approved by the maintainer on Windows/IngeTrazo. v0.42.1's updater changes are tested by isolated offline regression checks and Python compilation, not claimed as new GUI acceptance. GPL-3.0-or-later.
