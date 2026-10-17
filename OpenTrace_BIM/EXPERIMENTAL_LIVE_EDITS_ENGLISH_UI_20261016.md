# OpenTrace BIM — ISOLATED EXPERIMENTAL BUILD (2026-10-16)

**DO NOT PUBLISH OR MERGE WITHOUT EXPRESS USER AUTHORIZATION.**

This ZIP is a complete local successor to `OpenTrace_BIM-EXPERIMENTAL-ISOLADO-CORRECAO-RENDER-CACHE-BORDAS.zip`.
The actual GitHub repositories, branches, host IngeTrazo and official project notebooks were **not modified**.

## Changes

- **Immediate property edits**: the wall editor retains immediate parameter, assembly, material, and edge-finish updates through the native IngeTrazo history and viewport invalidation. Numeric text commits on Enter/focus loss, spin controls on action, combo selections on selection.
- **Common Layer / BIM / IFC properties**: remove the separate `Apply IFC properties` button. The predefined type, catalogue selection, classification system and classification code now commit directly. Unchanged values do not create redundant commands.
- **BIM selected-object panel**: remove `Apply BIM data`. Metadata text fields commit at Enter/focus loss, combo choices commit when selected. Update references using existing native metadata writer.
- **Advanced BIM**: semantic class/type, Pset value cells, IFC appearance (colour/opacity), and georeferencing fields now commit when the user finishes the edit. Saving reusable types, classifications, or named styles is still an explicit action. Applying a saved BIM type remains explicit.
- **Preset actions**: the preset command is labelled **Apply preset** and is reserved for replacing an existing configuration with the chosen reusable type.
- **English interface**: translated project setup, library management, layer combinations, wall/slab properties, layer composition, selected-object BIM controls, classification import/crosswalk/migration UI, advanced BIM sections, common alerts, and bundled UI labels. Only OpenTrace UI is forced to English. The host IngeTrazo and user-authored names, materials, library entries, IFC codes and identifiers are untouched.

## Validation

- `python -m compileall` — passed for the plugin source.
- `pytest -q OpenTrace_BIM/_experimental_tests` — **74 tests passed** (64 regression + 10 new source-level wiring checks).
- ZIP integrity checked with Python `ZipFile.testzip()`.

## Known limitations and test expectations

- PySide6 and the IngeTrazo graphical host are not installed in the build container. Therefore **Qt signal dispatch, viewport rendering, and the visual result on Windows are not yet validated**. Source-level wiring tests do not replace a host functional test.
- Special operations such as importing a catalogue, confirming crosswalk migration, and saving a named preset still require explicit user confirmation; these are not ordinary field edits.
- Some lower-priority status/log texts in legacy and specialized features may still need a subsequent locale audit after Windows screenshots. This package does not rename user-created content.
- The experimental IFC4.3 exporter still needs external schema/target-application conformance validation, independently of these UI changes.

## Suggested Windows checks

1. Select a composite wall. Change Wall top material: surface should repaint immediately. Change thickness and assembly parameters: update on Enter or focus loss with Undo/Redo.
2. Select a different bundled wall preset and press **Apply preset**: only this type-replacement action uses Apply.
3. In Layer / BIM / IFC, change PredefinedType or classification catalogue: no Apply button; selected object metadata updates on the selection.
4. In BIM, edit IFC name/type, classification system/code and common Pset fields; confirm with Tab/Enter, then Undo/Redo.
5. Open Advanced BIM, change semantic predefined type, Pset value, material appearance and georeference; inspect direct changes and re-open dialog.
6. Review project setup, layer composer, library browser and catalogue migration screens for remaining untranslated UI strings.
