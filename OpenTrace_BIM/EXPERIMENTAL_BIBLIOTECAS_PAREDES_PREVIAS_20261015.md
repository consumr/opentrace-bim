# OpenTrace BIM — experimental local: library selection, wall recipes and previews

**Scope:** based exclusively on `OpenTrace_BIM-EXPERIMENTAL-ISOLADO-CORRECAO-MALHA-MATERIAIS-COMPOSTOS.zip`. Never merge or publish automatically. No GitHub repository, branch, official decision book, or host program was modified.

## Library loading and selection

- `LibraryManagerDialog`: checkboxes on every collection, folder and resource, including partial states; `Select all / Deselect all` and a count of checked resources.
- Bottom-row `Import selected objects to project` imports checked recipes into the personal library; `Load checked libraries / objects` attaches selected full/partial collections to the current project. Selecting the tree row alone is still for preview and importing the current object explicitly.
- Mixed full-library and item/folder selection shows a confirmation explaining that both sets will load.
- Added a **real, selectable** `Architecture · Complete` built-in collection containing all bundled parametric presets and complex profiles. The optional complete index built with `Browse full library` is no longer silently ignored by the project selection action.
- Starter Basic/Standard packs now include key drywall/structural/wet-area recipes even when the master catalog grows. The project setup page preserves partial (not only whole-pack) selections when returning from the browser.
- Quick-tool preset list reads the actual checked recipes from `project_setup.resource_libraries`; the original full catalog remains browsable. No modeled instance is deleted or reclassified.
- Existing `.otlib` collections remain supported; a chosen subset is serialized with its source collection ID and just the checked recipes.

## Walls and defaults

- Added exposed clay brick (10/15 cm), exposed clay block (14/19 cm), structural concrete block (14/19/20 cm), brick + plaster, structural block + plaster, clay block 19 + plaster, concrete block wet-area cladding, and insulated drywall 95 mm.
- Added original procedural `OpenTrace · Clay Brick` texture. New concrete, clay, plaster, tile, gypsum, adhesive, steel and insulation layer materials refer to bundled native IngeTrazo material recipes. Existing customized walls/materials are not rewritten.
- The existing geometric junction fix from the prior package was left intact, not replaced.

## Previews

- The library wall preview is now a simple isometric sample, showing the external face, upper face and physical banding on the exposed wall end. It is **not** a full mesh render or a substitute for host 3D validation.
- The Layer Composer embeds a proportional physical layer stack preview, updated while editing the composition; both the floating and docked editors use it.

## Verification and limitations

- 50 Python automated regression tests passed, including 4 new tests of full/partial selections, quick tool availability, physical default textures and proportional preview positions.
- Python compilation and ZIP CRC validation performed.
- The PySide6/IngeTrazo Windows host is not installed in this environment. **The Qt dialogs, visual appearance, live wall mesh regeneration and undo/redo still need testing on Windows.**
- A full collection currently stores its selected recipes inside project BIM document metadata; optimize the saved footprint later if necessary. Personal names and project geometry are preserved.
- Door/window insertion defaults from favorite presets remain a separate pending integration.

## Windows acceptance checklist

1. In Home → Manage libraries, mark **Architecture · Complete** and confirm. In Wall list verify **Drywall 95 mm**, **Structural concrete block · 19 cm**, and **Clay brick + render on both sides** appear. Apply them to a copied test wall and inspect the scene/Undo.
2. Reopen the library browser. Check a few individual items only, confirm, and verify only those items (plus your personal presets) remain in the quick-list. Reopen the saved `.igz` and verify same selection.
3. Mark a complete pack plus selected items from another; confirm the mixed-selection warning. Try Select all / Deselect all.
4. Choose a wall preset and view the isometric library preview, including the exposed layered end; open Layer Composer and check the proportional colored bands change when a thickness or material changes.
5. Confirm native wall material defaults display in the viewport, then replace a layer with a custom material. Undo/redo and reopen the file. Check existing walls and IFC export are unchanged.
