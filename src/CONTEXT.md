# Src Workspace

Last updated: 2026-05-12

Source code lives here: agent orchestration, vendor tools, shared utilities, and tests. Use this workspace when changing behavior, adding tool packs, defining schemas, or wiring demo/live execution paths.

## Current Build Target

Approval-gated Five9 build path: read/preflight, core writes, modify/delete/rollback, IVR script XML discovery, and AI-usable IVR builder. Dry-run/stub mode is the default; live calls require explicit human approval and credentials.

## Code Structure

```
src/
  agent/                 # Agent orchestration and deterministic demo flow
  tools/                 # Platform tools; one operation per tool function
    Five9/
      common/            # Shared SOAP client and result helpers
      preflight_pack/    # Read/preflight tools
      core_config/       # Create/add/set write tools
      modify_config/     # Modify/update tools
      rollback_pack/     # Delete/remove rollback tools
      ivr/scripts/       # IVR script CRUD and xmlDefinition tools
      ivr/builder/       # IVR parser, catalog, compiler, and AI builder facade
    zoom_cc/             # Future Zoom Contact Center integration
    cxone/               # Future CXone integration
  utils/                 # Shared cross-platform utilities
  tests/                 # Agent, tool, SOAP, UI, and structure tests
```

Working Phase 1 code is in `src/tools/Five9/Prompt_Management/Prompt_Bulk_Upload/`.

## Agent Boundary

The graph can interpret, plan, request approval, execute approved calls, and record results. It must not contain Five9, Zoom CC, or CXone-specific branching. Platform-specific details belong in tool modules or adapter code.

## Tool Contract

- One tool performs one API operation.
- Tool filenames use `platform_operation.py`.
- Dry-run/stub mode logs the call and returns deterministic planned/mock results.
- Live mode is allowed only after explicit human approval and required credentials.
- Logs include tool name, parameters, timestamp, mode, result, and error details when present.
- Tools do not decide workflow order; the planner does.

## Planned Graph Nodes

1. `interpret` - parse business requirements into platform-neutral config actions
2. `plan` - map actions to ordered tool calls and parameters
3. `approve` - present the plan and wait for human approval
4. `execute` - run approved calls in stub or live mode
5. `log` - persist audit data to file or Supabase

## Testing Expectations

Test parsing, planning, approval blocking, dry-run/stub logging, SOAP envelopes, UI route gates, and platform adapter boundaries. Any code path that could call a live API must have a test proving it is blocked without approval.

## Local Environment

- Use `py` on Windows unless project tooling says otherwise.
- UI server: `cd UI` then `py app.py`.
- API docs are PDFs; use `pdftotext` before summarizing or coding from them.
- Do not add credentials to source files.
