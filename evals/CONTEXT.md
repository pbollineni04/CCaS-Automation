# Evals Workspace

Purpose: regression harnesses for the real CCaaS Automation Agent. Evals prove that playbooks produce validated, approval-ready Five9 operation inputs.

Rules:
- Keep eval fixtures and reports outside `src`; production agent code lives under `src/agent`.
- Evals may call the real local planner and validators, but must not execute live Five9 calls.
- Use sanitized or intentionally sample playbooks only.
- Expected outputs should focus on stable behavior: required tools, forbidden tools, minimum counts, and safety invariants.
- Write reports under `evals/reports/`.

Current harness:
- `agent_eval.py` runs playbook-to-plan eval cases.
- `cases/jacuzzi_playbook_agent_eval.json` covers the Jacuzzi converted playbook.
