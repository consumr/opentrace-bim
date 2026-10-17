# Installing OpenTrace BIM 0.42.1 — Alpha

**Host:** IngeTrazo 0.5.7+ (target; verify the installed host build). This Alpha release was functionally tested and approved by the maintainer on Windows/IngeTrazo; wider compatibility testing continues.

1. **Close IngeTrazo** and back up your existing extension folder and a copy of any `.igz` test project.
2. Open IngeTrazo → **Extensions → Open plugins folder** to locate the real user plugin directory, then close IngeTrazo.
3. Extract the ZIP and copy its single `OpenTrace_BIM` folder to that directory, replacing the **complete** existing folder. Do not mix Python files from older versions.
4. Verify the path is `.../ingetrazo/plugins/OpenTrace_BIM/__init__.py` (no nested duplicate folder).
5. Restart IngeTrazo and test using a **disposable** project before opening work files.

**Important:** This ZIP does not include `INSTALL_OPENTRACE_BIM.bat` or `INSTALL_OPENTRACE_BIM.py`. The one-click instructions in earlier historical packages therefore do not apply. Do not place backup directories named `OpenTrace_BIM_backup_*` inside IngeTrazo's scanned `plugins` folder; use a directory outside it.

In v0.42.1 and later, the updater directly checks the official OpenTrace BIM GitHub Releases feed. Users on v0.42.0 and earlier still need one update via IngeTrazo's external catalogue (or a manual installation), because their installed code has the former updater.
