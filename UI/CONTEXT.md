# UI Workspace

Last updated: 2026-05-06

The UI folder contains the local test interface for demonstrating the CCaaS Automation Agent. It is a FastAPI app with vanilla JavaScript served at `localhost:8000`.

## Purpose

Use this workspace to test the Phase 2 demo flow: load or paste discovery-template content, send it to the agent, display proposed configuration calls, show approval status, and show stub execution logs.

## Structure

```
UI/
  app.py              # FastAPI server
  requirements.txt    # UI runtime dependencies
  static/index.html   # Vanilla JS frontend
```

## Run Locally

From the workspace root:

```
cd UI
py app.py
```

## Boundaries

- The UI is a demo harness, not the orchestration layer.
- Do not put platform-specific planning logic in UI code.
- Do not execute live API calls from the UI.
- UI actions should call agent/tool code that enforces approval and stub/live mode.
- Display logs with tool name, parameters, timestamp, mode, and result.

## Good UI Work

Good UI work makes the CEO demo easy to follow: input, interpreted requirements, planned tool calls, approval gate, and stub results should be visible without needing to inspect terminal logs.
