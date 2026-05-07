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

## Safety Rules

- Tools are stubs until explicitly wired to live APIs.
- Live API calls require human approval.
- Every tool call must be logged with parameters, timestamp, and result.
- Platform-specific logic stays out of agent orchestration.
