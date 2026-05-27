# Agent Evals

This workspace holds regression evals for the real CCaaS Automation Agent.

The first harness verifies that a converted Five9 playbook produces validated, approval-ready Five9 operation inputs without executing live API calls.

## Run

```powershell
py evals/run_agent_eval.py
```

Equivalent module entry:

```powershell
py -m evals.agent_eval --case evals/cases/jacuzzi_playbook_agent_eval.json --report evals/reports/latest_jacuzzi_playbook_agent.json
```

## What It Checks

- the playbook can be parsed
- the agent produces planned Five9 tool calls
- the proposed write plan passes the executable schema
- required Five9 operations are present
- forbidden modify/delete/rollback/IVR XML operations are absent
- expected Jacuzzi skills, campaigns, DNIS, and IVR script shell create are present
- a JSON report is written under `evals/reports/`

## Add A Case

Create a new JSON file under `evals/cases/` with:

- `name`
- `playbook_path`
- `expected.ai_modes`
- `expected.min_counts`
- `expected.required_proposed_tools`
- `expected.forbidden_proposed_tools`
- optional required object names such as skills, campaigns, and DNIS numbers

Keep eval cases stable and focused on behavior that should not regress.
