# OpenTrace BIM 0.42.0 — Release Candidate

OpenTrace BIM 0.42.0 integrates the V9.1 hosted-door engine with expanded wall/material, IFC, classification and library workflows. This is a **pre-release candidate until Windows/IngeTrazo graphical acceptance is complete**.

## What's new

- Visual door-leaf compositor (front/isometric), traditional, glazed and panel configurations, material/profile settings, arched/sliding variants.
- Corrected independently clickable outer-frame checkboxes; new glazed/panel presets initialize perimeter ON without locking the controls.
- Editable groove count/width/margins/offset, improved isometric preview, dedicated Door panel and explicit Apply/Convert actions.
- Wall **Material Composer**, Simple/Composite conversion, immediate body/layer materials and four independently staged edge finishes using their own **Apply**.
- Unified new-project setup, resource libraries and favorites, materials/presets, layers and classification management.
- Existing IFC4 export plus experimental `IFC4X3_ADD2`, multi-system classification and reviewed catalog migration (no certified code-to-code equivalences).
- Additional English UI coverage and direct property updates with history commands.

## Limitations and risks

- Not yet visually validated on Windows/IngeTrazo; `.igz` save/reopen and external IFC round trips require real-host testing.
- Pocket sliding-door geometry and IFC4.3 conformance remain experimental. There is **no new complete window engine**.
- Grooves are shallow visual relief, not boolean-cut channels.
- Removing the perimeter from glazed/panel leaves may create an unsupported assembly.
- No bundled complete current ABNT/OmniClass/Uniclass datasets or normative mappings. Optional legacy Uniclass 2022 source is not current.
- Manual installation only. No `.bat` or Python installer is bundled.

## Validation completed before GitHub integration

100 general tests, 71 local door/editor tests, 3 merge tests, 12 focused door regression tests (some suites overlap), synthetic V7/V8 checks, compilation and archive integrity. **These do not substitute for live GUI testing.**

## Installation

Close IngeTrazo, back up the earlier plugin and extract the entire `OpenTrace_BIM` folder to the IngeTrazo plugins directory (Extensions → Open plugins folder). The file `OpenTrace_BIM/__init__.py` must exist without an extra nested `OpenTrace_BIM/` directory. Test on a disposable project first. Target: IngeTrazo 0.5.7+.

**Scope:** This is a consolidated inventory; it is not a verified `0.41.x → 0.42.0` git diff.
