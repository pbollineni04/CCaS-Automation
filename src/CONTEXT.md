# Src Workspace

Last updated: 2026-05-06

Source code lives here: LangGraph agent orchestration, vendor tools, shared utilities, and tests. Use this workspace when changing behavior, adding stub tools, defining schemas, or wiring demo execution paths.

## Current Build Target

Phase 2 demo: read a discovery template, interpret requirements, produce ordered Five9 configuration tool calls, require approval, and execute only stub tools that log parameters and timestamps.

## Code Structure

```
src/
  agent/          # LangGraph orchestration engine
  tools/          # Platform tools; one file per API operation
    Five9/        # Existing Five9 Phase 1 code and Five9 SOAP references
    zoom_cc/      # Future Zoom Contact Center REST stubs
    cxone/        # Future CXone REST stubs
  utils/          # Shared logging, config, parsing, SOAP helpers
  tests/          # Agent and tool tests
```

Working Phase 1 code is in `src/tools/Five9/Prompt_Management/Prompt_Bulk_Upload/`.

## Agent Boundary

The graph can interpret, plan, request approval, execute approved calls, and record results. It must not contain Five9, Zoom CC, or CXone-specific branching. Platform-specific details belong in tool modules or adapter code.

## Tool Contract

- One tool performs one API operation.
- Tool filenames use `platform_operation.py`.
- Stub mode logs the call and returns deterministic mock success.
- Live mode is allowed only after explicit human approval.
- Logs include tool name, parameters, timestamp, mode, result, and error details when present.
- Tools do not decide workflow order; the planner does.

## Planned Graph Nodes

1. `interpret` - parse business requirements into platform-neutral config actions
2. `plan` - map actions to ordered tool calls and parameters
3. `approve` - present the plan and wait for human approval
4. `execute` - run approved calls in stub or live mode
5. `log` - persist audit data to file or Supabase

## Testing Expectations

Test parsing, planning, approval blocking, stub logging, and platform adapter boundaries. Any code path that could call a live API must have a test proving it is blocked without approval.

## Local Environment

- Use `py` on Windows unless project tooling says otherwise.
- UI server: `cd UI` then `py app.py`.
- API docs are PDFs; use `pdftotext` before summarizing or coding from them.
- Do not add credentials to source files.
