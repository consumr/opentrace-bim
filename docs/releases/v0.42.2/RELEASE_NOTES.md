# OpenTrace BIM v0.42.2 — Alpha

Maintenance hotfix of the OpenTrace BIM v0.42.0/0.42.1 series.

## Fixed

- **Home → Check for updates is now enabled and connected.** Previous experimental isolation code inadvertently disabled both the manual button and the automatic-update checkbox, even though the background updater existed.
- Restores a single `UpdateManager` instance tied to the Home panel. The manual button checks releases when clicked.
- Restores saved, opt-in startup update checks. Turning the checkbox off cancels a scheduled check.
- Continues using **OpenTrace BIM GitHub Releases directly**, **not** the IngeTrazo catalogue; SHA-256 checks, version verification, safe ZIP extraction, explicit installation confirmation and required restart remain in effect.
- No architectural model/door/wall/IFC logic changes.

## Important for installations already in the field

**Users on v0.42.0 or v0.42.1 must install this version manually once**: both those published packages contain the same disabled Home update controls. They cannot discover v0.42.2 through that disabled button. Users on older v0.12.9 may have an active button but it consults IngeTrazo's independently maintained catalog, still announcing v0.12.9. No GitHub release can remotely modify already installed Python code.

After one v0.42.2 installation, future published ZIPs with matching release digest will be discovered by the button independently of IngeTrazo.

## Validation

Offline unit tests cover live updater-feed parsing and the Home wiring. Python syntax compilation and package checks run before publication. IngeTrazo/Windows runtime mouse testing of the new wiring remains to be performed; v0.42.0 modeling engine was separately approved by maintainer.

**Status:** Alpha; not release candidate. GPL-3.0-or-later.
