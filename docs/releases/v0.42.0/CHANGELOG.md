# OpenTrace BIM — Consolidated changes in v0.42.0 candidate

**Scope:** Features in the integrated 2026-10-16 local archive, not a commit/tag diff from any unverified 0.41.x series. The original archive declared internal `0.12.9`; the requested release identity is `0.42.0`. Presence in source does not imply completed Windows acceptance.

## Doors — motor and geometry

- Selectively merged V9.1 door engine with wall/IFC baseline; hosted swing door, opening-only, surface sliding and pocket sliding; canonical specs and host IDs.
- Gross opening dimensions and clearances, frames, curved heads, tracks/travel boundaries; experimental `pocket_layout='sleeve'`.
- Preserve wall/opening/door identity across conversion; host-native create/edit/delete history.
- Front/isometric visual leaf compositor with panel/glass/traditional presets, profiles, uniformity and per-element materials.
- Explicit Apply/Convert for families/types; creation defaults separated from selected-instance properties.
- Reordered leaf model controls after door system and before hardware. Preview caching and relayout mitigations; GUI confirmation still required.

## Final door-editor changes

- Extended English translation in Door inspector, editor, contextual toolbar, titles/tooltips.
- Always-expanded **MATERIALS — BY COMPONENT** section.
- Parametric traditional grooves: `groove_count`, `groove_width`, `groove_end_margin`, `groove_offset`; front/isometric painter improvements.
- Visible, independently interactive **Include side stiles** and **Include top/bottom rails** controls; new glazed/panel leaves start ON but users may turn them OFF.
- Last checkbox fix supersedes earlier checkbox-lock safety workaround.

## Walls, materials, composites

- Selected-instance Simple↔Composite conversion or new-wall configuration, with native Undo/Redo.
- Immediate body/layer material assignment and cache invalidation; independent end/top/bottom finishes.
- Four edge finishes (Start end, Finish end, Wall top, Wall bottom) are **staged** and require the dedicated **Apply**; selection change discards old pending edits.
- **Material Composer** opens the multilayer editor, including for already-composite walls. Preset Apply is for saved type replacement, not arbitrary property edits.
- More wall presets and proportional material/assembly previews.

## Project UI, libraries, BIM/IFC

- Start-focused Home, tools/modes icons, contextual values, layers and property synchronization inherited from earlier development.
- Project creation from empty/copy `.igz`/settings with independently chosen layer combination, IFC schema and libraries; saved settings should reopen directly.
- Library manager: tree, filters, multi-selection, `.otitem`, `.apreset`, `.otlib`, favorites, collections, import/export and previews; external texture embedding remains limited.
- Multi-system classification (Uniclass, ABNT, OmniClass, others), CSV/XLSX/ZIP import, manual review, IFC classifications and catalog migration with preview/Undo/provenance.
- IFC4 remains default; experimental `IFC4X3_ADD2`; sliding-door enums widened; no broad IFC importer rewrite.
- Optional historic Uniclass 2015 (Jan 2022) data retrieval; no full current normative catalog bundled.

## Existing compatibility and packaging

- Preserve walls/slabs/beams/columns/profiles, layers, IFC4 paths and existing `.igz` structures as far as source integration asserts; live compatibility acceptance outstanding.
- Membrane remains disabled since 0.12.9; independent older layer-combinations extension may coexist and needs examination.
- Release packaging changed version to `0.42.0`, instructions and docs; **no new production feature was coded in release preparation**.

**Conflict resolution:** checkbox FINAL correction supersedes older editor report; dedicated edge-finish Apply supersedes older immediate-edges description.
