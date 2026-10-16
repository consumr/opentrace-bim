# v0.42.0 — Known bugs, limitations, and unverified behavior

**Status meanings:** Fixed in code ≠ GUI verified; historical ≠ still reproducible; unverified ≠ confirmed broken.

| ID | Priority | Status | Issue / required validation |
| --- | --- | --- | --- |
| D-01 | High | Fixed in code; Windows unverified | Formerly non-clickable frame checkboxes; verify mouse/keyboard, independent toggle, mesh and Undo on glass/panels. |
| D-02 | High | Historical, mitigated | Door inspector relayout/jump on repeated dimension, jamb and opening changes; recheck scrolling. |
| D-03 | High | Previously approved, regression pending | Arch and Apply/Convert worked in earlier V9 tests; revalidate after merge for simple/composite walls. |
| D-04 | High | Unverified | Front/isometric painter, face order/culling, component materials could diverge from real viewport. |
| D-05 | High | Experimental | Sleeve/pocket sliding door with multilayer walls, cuts, IFC, quantities, saved legacy documents. |
| D-06 | Medium | Design limitation | Grooves are shallow relief, not real boolean cut/channels. |
| D-07 | Medium | Intentional risk | Users may turn off necessary frame around glazed/panel leaves; defaults ON, no enforced lock. |
| D-08 | Medium | Limitation | Plan angle disabled; opening percentage is static pose, not animation. |
| W-01 | High | Unverified | All four wall edge finishes require Apply; test on simple/composite walls, cache, Undo and persistence. |
| W-02 | High | Historical, not confirmed in candidate | Wall-length changes with hosted opening once caused viewport corruption; reproduction needed. |
| W-03 | Medium | Historical | Curved intersections, external T/curve combinations and performance remain regression targets. |
| BIM-01 | High | Experimental | IFC4X3_ADD2 declared but entity/Pset tables partly derive from IFC4; external conformance unverified. |
| BIM-02 | Medium | Data limitation | No certified ABNT/Uniclass/OmniClass code mappings or fully current packaged datasets. |
| BIM-03 | Medium | Unverified | Online SICLIC/bSDD, opt-in Uniclass 2022, CSV/XLSX/ZIP imports, offline/timeouts. |
| L-01 | Medium | Limitation | `.otlib` doesn't always embed external texture binaries; pre-insertion favorite door/window selection incomplete. |
| L-02 | Medium | Unverified | Potential duplicate configuration with independently installed layer-combinations extension; `.igz` initialization. |
| UI-01 | Medium | Unverified | Older dynamic texts/tooltips may still appear in Portuguese despite English UI expansion. |
| UI-02 | Medium | Unverified | Context bar/panel/viewport synchronization, focus/scroll after structural edits. |
| WIN-01 | High | Roadmap | New full parametric window engine not implemented. |
| PKG-01 | High | Stable-release blocker | Missing Windows/IngeTrazo acceptance, real `.igz` reopen and external IFC round-trip. |
| PKG-02 | Medium | Documentation corrected | Historical installer scripts were referenced but are not contained in ZIP; manual installation only. |
| OLD-01 | Historical | Fixed in 0.12.9; regression pending | Old global Qt event filter crash, backup extension duplication and UVW mapping regressions. |

Do not label historical issues as confirmed current defects without reproducing them; do not call code-level changes fully fixed until tested in the host.
