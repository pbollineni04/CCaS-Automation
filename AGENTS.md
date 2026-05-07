# CCaaS Automation Agent

AI agent that turns client requirements into approved contact center configuration calls.
Stack: Python, LangGraph, Anthropic Claude API, Supabase. Platforms: Five9 primary, Zoom CC, CXone.

## Workspaces
- /planning - specs, architecture decisions, API research
- /src - agent code, platform tools, utilities, tests
- /docs - API notes, guides, demo scripts
- /UI - local FastAPI demo UI

## Routing
| Task | Go to | Read |
|-|-|-|
| Spec a feature, design architecture, research APIs | /planning | CONTEXT.md |
| Write agent, orchestration, tool, utility, or test code | /src | CONTEXT.md |
| Work on Five9 Phase 1 tools or Five9 API PDFs | /src/tools/Five9 | CONTEXT.md, then /src/CONTEXT.md |
| Work on the local demo UI | /UI | CONTEXT.md, then /src/CONTEXT.md |
| Write API notes, guides, or demo scripts | /docs | CONTEXT.md |

## Naming
- Specs: `feature-name_spec.md`
- Decisions: `YYYY-MM-DD-decision-title.md`
- Tools: `platform_operation.py` such as `five9_create_prompt.py`
- Tests: `test_toolname.py`
- Demo scripts: `demo-name_script.md`

## Rules
- Stub tools only until explicitly told to wire live APIs
- Never execute live API calls without human approval
- Log every tool call with parameters, timestamp, and result
- Each tool performs one API operation only
- Keep platform-specific logic out of agent orchestration
- API docs are PDFs; use `pdftotext` to read them
