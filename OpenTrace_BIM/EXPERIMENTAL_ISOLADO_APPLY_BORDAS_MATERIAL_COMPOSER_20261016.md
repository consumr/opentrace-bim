# OpenTrace BIM — EXPERIMENTAL · ISOLADO · Wall edge Apply + Material Composer

**Data:** 16 October 2026  
**Input:** `OpenTrace_BIM-EXPERIMENTAL-ISOLADO-PAREDES-COMPOSITE-MATERIAIS-IMEDIATOS-20261016.zip`  
**Scope:** Local ZIP only. No GitHub or other project files changed.

## Requested changes

1. **One Apply for wall edge materials.** Added an **Apply** button directly below the four material selectors `Start end`, `Finish end`, `Wall top`, and `Wall bottom`, inside the wall-property panel. Selection changes now **stage** their materials; the scene is modified only when this Apply is clicked. All four finishes are committed together with the pre-existing `PaintWallEdgeFinishes` history command. This does not call or repurpose `Apply preset`, and does not rebuild wall geometry. The painter supports simple and composite walls.
2. **No accidental paint of other objects.** If selection or document changes before Apply, the pending edge-paint request is discarded instead of writing to another wall. Pending choices survive refreshes and edits to other parameters on the same wall. Changing unrelated wall dimensions does not implicitly commit these staged finishes. With no wall selected, Apply only stores finishes for the next wall.
3. **Composite → Material Composer.** The **Composite** button in the wall contextual bar is renamed **Material Composer**. Clicking it configures/changes the actual wall type (existing logic), then opens the **existing floating layer editor**, including when the wall was already composite. The popup title is also **Material Composer**. The wall-tool menu's Composite action opens the same editor; the Simple action remains separate. No new layer engine was created.
4. Opening the floating editor again brings an existing open window forward instead of creating duplicate dialogs. The explanatory hint now acknowledges the new edge Apply exception.

## Production files changed

- `ui.py`: one Apply below edge selectors, staging/commit, selection guard, prevents indirect committing of pending edge materials, open Material Composer action.
- `contextual_bar.py`: button caption and invocation of the existing composer, refresh of selection before conversion.
- `layer_ui.py`: dialog title and single-open-window behavior.

## Tests and scope of validity

- `python -m pytest -q OpenTrace_BIM/_experimental_tests`: **100 passed**, including retained regression tests and new tests for staged Apply, simple and composite commands, creation defaults, selection-change safety, and the contextual-button/editor wiring.
- `python -m compileall -q OpenTrace_BIM`: passed.
- Existing `PaintWallEdgeFinishes` was executed with test doubles of mesh faces, scene, history, and host. Its writes, persistence metadata, Undo/Redo and cache invalidation signals were checked by automated tests.
- **Not tested inside actual IngeTrazo Windows.** PySide6 and IngeTrazo's native rendering scene were unavailable in this Linux environment. Test success does not prove actual Windows UI click, texture application, rendering, persistence of `.igz`, or Undo/Redo in that host. The user must perform graphical acceptance.

## Suggested Windows acceptance check

1. Select a **Simple** wall; change `Start end`, `Finish end`, `Wall top`, `Wall bottom`. Verify *no change before* pressing the small **Apply** directly under those four selectors; press it once and inspect all surfaces.
2. Repeat with a **Composite** wall with at least two layers. Verify `Use layer material`, independently colored surfaces, and no geometry changes.
3. Click **Material Composer** on an already composite wall. The editor should open even without changing the radio-button state. Click it on a simple wall: conversion followed by the editor should occur.
4. Edit a layer material in the popup; verify the actual object is updated. Close and reopen the popup. Use Undo/Redo, change height/thickness, save/reopen `.igz`.
5. Start changing edge colors on wall A, select wall B without pressing Apply; check that pressing Apply cannot paint B using A's pending colors.

**Package remains EXPERIMENTAL — ISOLADO.** No Windows graphical acceptance is claimed.
