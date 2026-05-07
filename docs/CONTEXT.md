# Docs Workspace

Last updated: 2026-05-06

Docs holds API notes, guides, onboarding material, and demo scripts. Use this workspace when producing material a stakeholder, engineer, or future agent can read without digging through source code.

## Structure

```
docs/
  api/            # Processed API notes per platform
  guides/         # How-to and architecture guides
  demo-scripts/   # Scripted stakeholder demos
```

## Source API Material

Vendor PDFs stay with the related integration work, especially `src/tools/Five9/`. Docs should hold extracted notes, quick references, and cross-links back to source PDFs. Use `pdftotext` before summarizing PDF contents.

## Demo Script Format

```
# Demo: Name
## Setup
## Script
## Expected Output
## Talking Points
## Recovery
```

Demo scripts use `demo-name_script.md`.

## Current Priorities

1. CEO demo script for Phase 2: discovery template to Five9 stub calls
2. Five9 prompt operation quick reference
3. Architecture guide explaining orchestration, approval, stubs, and logging

## Good Docs Output

Good docs are operational: concrete inputs, expected outputs, commands, screenshots only when useful, and recovery steps for demos. API notes should cite the source PDF name and extraction date.

## Avoid

- Copying long raw PDF text into docs
- Documenting live API behavior that has not been tested
- Mixing stakeholder demo language with engineer implementation notes in the same section
