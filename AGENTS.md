# CCaaS Automation Agent

AI agent that turns client requirements into approved contact center configuration calls.
Stack: Python, LangGraph, Anthropic Claude API, Supabase. Platforms: Five9 primary, Zoom CC, CXone.

## Workspaces
- `/planning` - specs, architecture decisions, API research
- `/src` - agent code, platform tools, utilities, tests
- `/docs` - API notes, guides, demo scripts
- `/UI` - local FastAPI demo UI

## Routing
| Task | Go to | Read |
|-|-|-|
| Specs, architecture, API research | `/planning` | `CONTEXT.md` |
| Agent, orchestration, tools, utilities, tests | `/src` | `CONTEXT.md` |
| Five9 tools, SOAP code, IVR builder | `/src/tools/Five9` | `CONTEXT.md`, then `/src/CONTEXT.md` |
| Local FastAPI UI | `/UI` | `CONTEXT.md`, then `/src/CONTEXT.md` |
| API notes, guides, demo scripts | `/docs` | `CONTEXT.md` |

## Naming
- Specs: `feature-name_spec.md`
- Decisions: `YYYY-MM-DD-decision-title.md`
- Tools: `platform_operation.py`, placed in the correct vendor pack
- Tests: `test_toolname.py`
- Demo scripts: `demo-name_script.md`

## Safety
- Dry-run/stub mode is the default.
- Live tool calls require explicit human approval.
- Never store credentials in source files.
- Log every tool call with parameters, timestamp, mode, and result.
- Each tool performs one API operation only.
- Keep platform-specific logic out of agent orchestration.
- API docs are PDFs; use `pdftotext` or extracted notes before coding from them.
