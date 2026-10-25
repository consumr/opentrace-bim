# ArchTrace BIM — standalone workspace

> Early-stage workspace for a future standalone OpenTrace BIM experience. This folder is not yet a released application and does not rename or replace the existing plugin.

## Why this workspace exists

An independent viewport and a simple, direct installation path may make it easier for architects, testers and developers to discover the project, report bugs, propose improvements and contribute.

## Goals

- Allow newcomers to open, inspect and eventually edit BIM models without installing the current IngeTrazo host first.
- Reuse and progressively isolate existing parametric architectural logic rather than rewriting it prematurely.
- Make bug reports, reproducible test files and contributions straightforward.
- Preserve compatibility with the existing OpenTrace BIM plugin while independence is evaluated.

## Initial boundaries

- **Core:** shared architectural definitions, persistence contracts and parametric operations (to be extracted carefully).
- **Viewport:** rendering, selection, navigation and interaction, independent of the current host.
- **Adapters:** bridge the shared BIM core to the standalone UI and the IngeTrazo plugin.
- **Community:** sample projects, reproducible bugs and contribution guidance.

## First milestone — playable prototype

1. Launch a viewport with one click or a simple install.
2. Display a sample scene containing a wall, slab, beam and column.
3. Select an element and inspect its semantic/parametric properties.
4. Save and reopen a sample model reliably.
5. Link users directly to a bug report and contribution instructions.

## Compatibility and licensing

Existing OpenTrace BIM code and its GPL-3.0-or-later license and attribution requirements must be respected. No assumptions are made yet about a new application framework or file format.

## Status

Planning scaffold only; architecture, packaging and final product branding remain to be validated.
