# v0.42.0 — Windows/IngeTrazo acceptance checklist

**All cases initially NOT EXECUTED.** Record Windows build, IngeTrazo commit/version (target 0.5.7+), language, GPU driver, previous plugin and install path. Use disposable/sanitized `.igz` files and independent backups.

- [ ] Load plugin, Home, tool palettes and contextual panels without crash or duplicate menus; focus, Escape/Space and scrollbar behavior.
- [ ] Insert swing, glazed/paneled, arched, sliding, pocket and opening-only doors by click and numeric input; inspect front/back geometry.
- [ ] Edit/Convert doors; preserve GUID/wall/opening and host link; Undo/Redo, delete and restore without orphan openings.
- [ ] Door composer opened without and with selected instance: independently toggle side stiles/top-bottom rails with mouse and keyboard; new glass/panel presets start ON but remain clickable.
- [ ] Verify profiles, per-component materials, uniformity, 2D and isometric from 45/90/180/270 degrees; no missing faces.
- [ ] Grooves: change count 3→5, width 3→5 mm, end margin 100→150 mm, offset +12 mm; verify host, preview, undo and reopen.
- [ ] English-only UI audit; MATERIALS — BY COMPONENT always visible; model controls before hinges; no recurring layout/scroll jump.
- [ ] Simple and composite walls: body/layer materials update immediately; start/finish/top/bottom finish selectors take effect only after dedicated Apply.
- [ ] Wall A uncommitted border edits do not leak into Wall B on selection switch/Apply; verify Undo/Redo, saved materials and cache.
- [ ] Material Composer opens for simple/composite selected walls without duplicated dialogs; convert simple/composite; edit wall length with hosted openings to check old viewport corruption bug.
- [ ] Save/close/reopen `.igz`: doors, wall layers, edge paints, materials, GUID/IDs, clearance/profiles remain editable.
- [ ] New project template/layer combination/library/classification setup; copy `.igz` without overwriting original; reopen without unwanted wizard.
- [ ] Library manager: `.otlib` import/export, favorites, offline missing textures, external CSV/XLSX/ZIP, mixed classification migration with conflicts/Undo.
- [ ] IFC4 default export/import with opening, width/height, materials and classification tested in Archicad and another reader.
- [ ] Experimental IFC4.3 independently validated with IfcOpenShell or equivalent; preserve warnings and limitations.
- [ ] Old crash regressions: disabled Membrane, no Qt filter crash, no duplicate extensions/paths after install.
- [ ] Confirm update checker not auto-installing this candidate; no nonexistent installer referenced as included.

## Report a failure

Include ID, OS/host/plugin versions, exact reproduction steps, expected/actual behavior, console logs, screenshot/video, sanitized `.igz` sample, Undo/Redo impact and severity.

**Gate:** technical review and a pre-release may precede acceptance; a stable release requires all critical checklist items and explicit maintainer signoff.
