# Planning Workspace

Last updated: 2026-05-12

Planning holds specs, architecture decisions, and API research for the CCaaS Automation Agent. Use this workspace when deciding what to build, how vendor integrations should fit the shared engine, or how an API behaves before code is written.

## Current Phase

Phase 1 is complete: Five9 prompt bulk upload works in `src/tools/Five9/Prompt_Management/Prompt_Bulk_Upload/`.

Current build focus is the approval-gated Five9 path: live-capable preflight reads, dry-run/live core writes, modify/delete/rollback, IVR script XML discovery, and the AI-usable IVR builder. Demo mode remains deterministic where appropriate.

## Architecture Principles

- The orchestration engine is platform agnostic.
- Vendor behavior lives behind adapter/tool boundaries.
- New vendor support should require a new adapter, not changes to the graph.
- Human approval is required before live execution.
- Dry-run/stub mode is the default.
- Live API execution requires explicit human approval and credentials.
- Every proposed and executed tool call must be auditable.

## Target Flow

```
requirements document / discovery template / chat
-> interpret requirements
-> plan ordered configuration actions
-> present human approval request
-> execute approved stub or live tools
-> log parameters, timestamps, results, and state changes
```

## Configurable Entities

Prompts, IVR/IVA flows, routing rules, queues, users, permissions, campaigns, DNIS assignments, and third-party integrations. Plans should model create, modify, and delete actions without mixing multiple API operations into one tool.

## API Research Status

| Platform | API type | Source location | Status |
|-|-|-|-|
| Five9 | SOAP v13 | `planning/api-research/five9/`, `src/tools/Five9/` | Active tool packs |
| Zoom CC | REST | `planning/api-research/zoom_cc/` | Not started |
| CXone | REST | `planning/api-research/cxone/` | Not started |

## File Organization

- Specs: `planning/specs/feature-name_spec.md`
- Architecture notes: `planning/architecture/topic.md`
- Decisions: `planning/decisions/YYYY-MM-DD-decision-title.md`
- API research: `planning/api-research/platform/topic.md`

## Good Planning Output

Good planning output defines the business goal, config entities affected, platform-neutral action model, vendor-specific constraints, approval boundary, logging requirements, demo value, and test strategy.

## Avoid

- Placing platform-specific behavior in orchestration specs
- Treating dry-run/stub output as proof of live API behavior
- Reading entire API PDFs when a focused extracted note will do
- Expanding Zoom CC or CXone before the Five9 Phase 2 demo path is clear
