# Folder Architecture Breakdown for CCaaS Automation Agent

Date: 2026-05-06

This note translates the walkthrough's three-layer folder architecture into the CCaaS Automation Agent project. The goal is to make the agentic builder faster, more efficient, and more reliable by giving every task a clear home, loading only the context needed for that task, and keeping vendor-specific implementation details out of the shared orchestration layer.

## Walkthrough Lessons Applied

### 1. CLAUDE.md is the map, not the whole project brief

The root `CLAUDE.md` should stay short. Its job is to tell the agent what the project is, where the workspaces are, which context file to read for each task, the naming conventions, and the non-negotiable safety rules. The walkthrough warns that a long root file wastes context and buries the routing instructions. For this project, detailed architecture, Five9 SOAP notes, UI behavior, and demo details belong in workspace context files instead of the root.

Applied here:

- `CLAUDE.md` stays under 40 lines.
- It routes planning, source code, docs, Five9, and UI work to the right folder.
- It keeps only durable rules: stub-first, approval before live API calls, per-tool logging, one API operation per tool, and no platform logic in orchestration.

### 2. Workspace CONTEXT.md files are the rooms

The walkthrough's second layer is the workspace context file. Each workspace describes the work that happens there, the files that belong there, and what good output looks like. This is the biggest speed improvement for the CCaaS builder because the agent can read the context for the current task without loading every API note, demo script, and source file.

Applied here:

- `planning/CONTEXT.md` covers architecture, specs, API research, and the current Phase 2 demo goal.
- `src/CONTEXT.md` covers the LangGraph graph, tool contract, tests, and platform boundary.
- `docs/CONTEXT.md` covers API notes, guides, demo scripts, and documentation standards.
- `UI/CONTEXT.md` covers the local FastAPI demo harness.
- `src/tools/Five9/CONTEXT.md` covers Five9-specific SOAP notes and the existing Phase 1 tool.

This creates a practical memory hierarchy. A demo-script task reads docs context. A tool task reads source context. A Five9 SOAP task reads Five9 context first, then general source context.

### 3. Layer 3 tools load only where they are needed

The walkthrough's third layer is tools, skills, or other plug-in capabilities. In this project, the most important Layer 3 concept is the platform tool boundary: Five9, Zoom CC, and CXone tools are swappable integration layers beneath a shared orchestration engine.

Applied here:

- Platform operation files live under `src/tools/`.
- Each tool does one API operation.
- Stubs are the default Layer 3 behavior during Phase 2.
- Live API execution is blocked unless a human explicitly approves it.
- The agent graph plans and dispatches calls but does not know SOAP or REST details.

This keeps the agent fast because it does not reason through every vendor API on every request. It keeps the system safer because all external side effects sit behind explicit tool functions and approval checks.

### 4. Routing tables prevent guessing

Without routing, the agent has to infer where to look and may read the wrong files. The walkthrough treats routing as the difference between consistent output and inconsistent output. For this project, routing is especially important because the repo contains both working Phase 1 Five9 code and new Phase 2 stub work.

Applied here:

- Feature specs and API research route to `planning/`.
- Agent, tool, utility, and test code route to `src/`.
- Five9-specific work routes to `src/tools/Five9/`.
- Demo UI work routes to `UI/`.
- Guides and demo scripts route to `docs/`.

That reduces context drift. A request like "add a Five9 queue stub" should not start by reading demo scripts. A request like "write the CEO walkthrough" should not start by editing SOAP code.

### 5. Naming conventions act like a lightweight index

The walkthrough emphasizes that naming conventions help the agent find and organize files without a database. That matters here because the system will grow across specs, decision records, API notes, tools, tests, and demo scripts.

Applied here:

- Specs use `feature-name_spec.md`.
- Decisions use `YYYY-MM-DD-decision-title.md`.
- Tools use `platform_operation.py`, such as `five9_create_prompt.py`.
- Tests use `test_toolname.py`.
- Demo scripts use `demo-name_script.md`.

These names make the folder tree predictable. Predictability makes future agent work faster because it can infer where a file should exist and what related test or spec should be called.

### 6. Context files are living notes

The walkthrough warns that stale context causes output drift. The CCaaS builder will change quickly as Phase 2 moves from a demo to real execution, then to multiple vendors. Each context file now has a `Last updated` line to make staleness visible.

Applied here:

- When a vendor API is researched, update `planning/CONTEXT.md` and add notes under `planning/api-research/platform/`.
- When a tool contract changes, update `src/CONTEXT.md`.
- When the demo flow changes, update `docs/CONTEXT.md` and `UI/CONTEXT.md`.
- When Five9 live behavior is confirmed, update `src/tools/Five9/CONTEXT.md` with the tested operation and source evidence.

## How This Makes the Builder Fast

The agent gets faster by loading the smallest useful context for the task. The root map tells it where to go, and each workspace gives it enough local rules to start without re-reading the whole project. For the CEO demo, a request can route directly through `docs/` for the script, `UI/` for the visible harness, and `src/` for the stub planning path. It does not need to read Zoom CC or CXone notes while building the Five9 demo.

The same pattern applies at runtime. The orchestration engine should interpret requirements into platform-neutral actions, then map only the selected platform's actions to tool calls. A Five9 demo should not load Zoom CC or CXone adapters. A prompt upload operation should not load queue, DNIS, and campaign logic unless the plan requires those entities.

## How This Makes the Builder Efficient

Efficiency comes from separation of concerns:

- Planning files decide what should exist.
- Source files implement how the agent and tools behave.
- Docs explain how to use or demo the system.
- Five9 files hold Five9-specific SOAP knowledge.
- UI files present the demo without owning business logic.

This keeps implementation work local. If the queue stub is wrong, fix the queue tool and its tests. If the agent plans operations in the wrong order, fix the planner. If the CEO demo is unclear, update the demo script and UI presentation. The folder structure prevents one task from spreading across unrelated areas.

Efficiency also comes from the one-operation tool rule. A tool like `five9_create_prompt.py` is easier to test, log, approve, and eventually replace with a live implementation than a broad `five9_manage_prompts.py`. Atomic tools make the approval screen clearer because each planned action maps to a single auditable operation.

## How This Makes the Builder Work Well

"Works well" for this project means more than producing plausible tool calls. It means the agent produces a reviewable change plan, blocks live side effects until approval, logs every action, and keeps vendor-specific logic contained.

The folder architecture reinforces those requirements:

- The root rules make safety non-negotiable.
- `src/CONTEXT.md` requires tests for approval blocking and stub logging.
- `src/tools/Five9/CONTEXT.md` keeps Five9 SOAP constraints near the Five9 code.
- `planning/CONTEXT.md` keeps architecture decisions explicit before implementation.
- `docs/CONTEXT.md` keeps demo language and operator guides separate from code internals.

For the CEO demo, the intended visible flow is:

1. Provide a discovery template.
2. Show interpreted business requirements.
3. Show ordered Five9 configuration calls.
4. Show that approval is required.
5. Execute in stub mode after approval.
6. Show logged tool calls with parameters, timestamps, mode, and results.

That sequence demonstrates the real product architecture without risking a live CCaaS environment.

## Practical Maintenance Rules

- Keep the root `CLAUDE.md` short. Move details into context files.
- Add new workspaces only when the mental mode changes. Otherwise add subfolders.
- Update context files when architecture, APIs, or demo behavior changes.
- Keep API PDF extraction notes focused and cite the source PDF.
- Treat stub/live mode as an explicit boundary in specs, code, docs, and demos.
- Prefer platform-neutral action models in planning and platform-specific operation tools in `src/tools/`.

This setup should stay small enough to use immediately and structured enough to grow into live Five9, Zoom CC, and CXone integrations without turning the root prompt or orchestration layer into a vendor-specific catch-all.
