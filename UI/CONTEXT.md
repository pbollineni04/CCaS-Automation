# UI Workspace

Last updated: 2026-05-12

The UI folder contains the local operator interface for demonstrating and exercising approval-gated CCaaS tools. It is a FastAPI app with vanilla JavaScript served at `localhost:8000`.

## Purpose

Use this workspace to test discovery-template demos, Five9 preflight reads, approval-gated dry-run/live tool packs, IVR XML discovery, and the IVR builder. UI code should call pack dispatchers and facades; business/tool behavior belongs in `src/`.

## Structure

```
UI/
  app.py              # FastAPI server
  requirements.txt    # UI runtime dependencies
  static/index.html   # Main tools UI
  static/demo.html    # Deterministic CEO demo flow
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
- Live calls from UI routes must require approval and credentials before creating clients.
- UI actions should call agent/tool pack dispatchers and facades that enforce approval and dry-run/live mode.
- Display logs with tool name, parameters, timestamp, mode, and result.

## Good UI Work

Good UI work makes the CEO demo easy to follow: input, interpreted requirements, planned tool calls, approval gate, and stub results should be visible without needing to inspect terminal logs.
