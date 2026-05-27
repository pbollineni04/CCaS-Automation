# CCaaS Automation

AI agent for converting contact center requirements into approved configuration calls.

## Stack

- Python
- LangGraph
- Anthropic Claude API
- Supabase
- FastAPI demo UI

## Platforms

- Five9 primary
- Zoom Contact Center
- NICE CXone

## Workspace Layout

- `planning/` - specs, architecture decisions, and API research
- `src/` - agent code, platform tools, utilities, and tests
- `docs/` - API notes, guides, and demo scripts
- `UI/` - local FastAPI demo UI

## Five9 Tool Packs

- `src/tools/Five9/preflight_pack/` - read and preflight inspection
- `src/tools/Five9/core_config/` - create/add/set operations
- `src/tools/Five9/modify_config/` - modify/update operations
- `src/tools/Five9/rollback_pack/` - delete/remove rollback operations
- `src/tools/Five9/ivr/scripts/` - IVR script CRUD and XMLDefinition tools
- `src/tools/Five9/ivr/builder/` - AI-usable IVR build kit and compiler

## Safety Rules

- Dry-run/stub mode is the default.
- Live tool calls require explicit human approval.
- Every tool call must be logged with parameters, timestamp, mode, and result.
- Platform-specific logic stays out of agent orchestration.
