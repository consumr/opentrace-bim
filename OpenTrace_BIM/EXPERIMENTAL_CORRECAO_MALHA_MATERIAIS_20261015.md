# OpenTrace BIM — EXPERIMENTAL ISOLADO / Wall mesh + layered materials

**15 October 2026. DO NOT PUBLISH OR INTEGRATE INTO OTHER BRANCHES/DOCUMENTS WITHOUT EXPRESS AUTHORISATION.**

Base ZIP: `OpenTrace_BIM-EXPERIMENTAL-ISOLADO-ENGLISH-UI-MATERIAIS.zip`.
Changes are local to this isolated package; previous ZIP remains intact. No GitHub writes.

## 1. Composite wall junction caps

Root-cause hypothesis from source inspection: junction resolver calculates start/end cap vertices at the two OUTSIDE boundaries of the entire wall. `build_children` used to pass those same full-width endpoints to each constituent layer, including 5–15 mm finishes, thereby stretching thin layer cross-sections across the entire wall at joined endpoints. This could produce spikes, crosses and broken-looking edges when changing a wall preset, particularly at corners and multiwall intersections.

`model._caps_for_layer` now interpolates each layer's start/end cap endpoints between the full-wall endpoints, proportionally to the layer's actual offset band. Stored caps and reference axes remain unchanged, so editing, joins and Undo still use the original host geometry. When a preset changes, face appearance is inherited only from the same named layer; an unrelated layer occupying the previous list position is no longer a source of inappropriate appearance/UVW.

## 2. Layered defaults for bundled wall styles

The built-in composite wall presets now declare actual `material_name` values on their component layers. Each material is lazily registered into the standard IngeTrazo `scene.materials` registry when used, and its texture/color is applied to the generated faces. Nine small, original procedural raster textures ship in `assets/default_materials/`:

- OpenTrace · Light Plaster
- OpenTrace · Clay Block
- OpenTrace · Concrete Block
- OpenTrace · Ceramic Tile
- OpenTrace · Gypsum Board
- OpenTrace · Concrete
- OpenTrace · Tile Mortar
- OpenTrace · Steel
- OpenTrace · Mineral Insulation

The outermost visible layers determine the visible face. Brick inside plaster remains physically concealed until the layer is exposed, as required by wall composition. All preset defaults can be replaced by selecting another material for the individual layer. Existing project layers are not silently rewritten on opening, and the scene material registry overrides the bundled recipe if a user uses the same material name for a custom recipe.

Textures are original procedural illustrations; they are not manufacturer finishes or engineering/certification data. Material layers, thicknesses and IFC classifications were not changed.

## 3. Validation

- Python `compileall` passed.
- All 46 host-free automated tests passed, including 5 new regression tests for the cap distribution, preset switch, texture file integrity, per-layer default material assignment and custom material override.
- ZIP integrity verified during packaging.

**Not validated:** actual PySide6 / IngeTrazo Windows rendering and interactive junction geometry. Test straight and L/T joint walls, a seven-layer ceramic-clad wall, a plain-render wall and Undo/Redo after switching presets. Previously painted custom faces should be verified as well. A source-level diagnosis is not proof that all mesh corruption causes are eliminated.

## 4. Scope

No changes to IngeTrazo source, BIM exporter, door and window engines, official GitHub branches, external notebooks or other archives.
