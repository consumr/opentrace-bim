# OpenTrace BIM 0.42.0 — Release Candidate

**Prepared:** 16 October 2026 · **Status:** release candidate / Windows QA pending. This consolidated candidate was assigned release version 0.42.0; the local experimental source identified itself internally as 0.12.9. This is not a verified diff against the latest GitHub 0.41.x release, nor a verified stable release. Target host: IngeTrazo 0.5.7+; GPL-3.0-or-later.

## Highlights

- **Integrated door engine V9.1:** dedicated Door panel, visual 2D/isometric leaf composer, traditional and configurable panel/glazed leaf designs, per-component profiles/materials, continuous arched frame/trim, hinged/apparent sliding/pocket sliding variants, and explicit **Apply/Convert** for changing an existing door's family while retaining hosted identity.
- **Door editing corrections:** English UI additions, non-collapsible **MATERIALS — BY COMPONENT**, user-editable traditional grooves (count, width, end margin, lateral offset), improved isometric ordering, and accessible side-stile / top-bottom-rail checkboxes. New framed panel/glazed presets start with the perimeter checked, **but users may switch it off**.
- **Walls and materials:** simple/composite conversion, independent material selection and layer materials, four distinct end/top/bottom surface finishes, staged **Apply** directly under these four selectors, and **Material Composer** opening the existing layer dialog. The edge-finish Apply is distinct from **Apply preset**, which remains for saved types.
- **Project setup and libraries:** unified new-project setup for project templates, layer combinations, IFC scheme, classification catalogues and libraries; reusable favorites, catalog search, collection selection/import/export and wall recipe previews. Existing `.igz` projects are not forced through a new setup wizard.
- **BIM interoperability:** IFC4 as the default, experimental IFC4X3_ADD2 export option; Archicad/Revit/Bonsai/OpenTrace-oriented export profiles preserved. Multiple catalogue systems, reviewed equivalence records, guided catalogue migration and manual classifications, with source/provenance tracking. No invented national classification codes.
- **Immediate editing where appropriate:** regular property changes, main/layer material changes, and editable BIM metadata use existing host history integration; wall edge finishes intentionally require **Apply**. Compound/saved-preset conversions remain explicit.

## Important compatibility and limitations

- **Windows acceptance is not complete.** Python tests cannot certify mouse interactions, GPU rendering, real host command/history, `.igz` reopens or IFC use in Archicad/Revit/Bonsai/FreeCAD.
- The new pocket sliding assembly is experimental (wall composites, offsets, quantities and IFC require real-model validation). Historic pocket geometries are not auto-migrated.
- A full new parametric **window engine was not implemented**: existing window flow and optional V9.1 visual composition were preserved.
- Traditional groove relief uses shallow face-applied features, not boolean-cut grooves with configurable depth.
- IFC4.3 metadata/property schema content is not a complete upgraded IFC4.3 catalogue; generated files have not undergone independent conformance validation. IFC4 remains the prudent default.
- Official complete 2026 Uniclass/OmniClass/ABNT datasets or certified code-level equivalences are not included. An optional historic Uniclass 2022 download is not current Uniclass.
- A user can intentionally turn off the perimeter on a glazed/panel leaf, which may result in a physically unsupported configuration. For new framed presets the perimeter begins on.
- Language translation coverage is improved but comprehensive English UI verification still requires a real Windows walk-through.
- The Membrane tool remains dormant / under evaluation from the 0.12.9 base.
- **No automatic installer is included.** Install manually according to `INSTALL.md`.

## Release gate

Before marking GitHub release as stable: complete `QA_WINDOWS_0.42.0.md` in the accompanying handoff ZIP; test against a backed-up copy of both new and existing `.igz` projects, and validate representative exports externally. Until then use GitHub **Pre-release**, if publication is explicitly approved.

## Provenance

This candidate uses the complete uploaded isolated fix-check-box ZIP from 16 October 2026. It retains the merged walls/IFC/doors baseline and the final checkbox correction. The original merge and experimental reports are retained as historical records and may contain statements superseded by later fixes.
