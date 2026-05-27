from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.agent.graph import run_playbook_agent
from src.agent.schemas import validate_agent_executable_plan


FORBIDDEN_XML_KEYS = {"xmlDefinition", "xml_definition"}


def load_eval_case(case_path: str | Path) -> dict[str, Any]:
    path = Path(case_path)
    if not path.exists():
        raise FileNotFoundError(f"Eval case not found: {path}")
    case = json.loads(path.read_text(encoding="utf-8"))
    _require_string(case, "name")
    _require_string(case, "playbook_path")
    if not isinstance(case.get("expected"), Mapping):
        raise ValueError("Eval case expected must be an object")
    return case


def run_eval_case(
    case_path: str | Path,
    *,
    repo_root: str | Path | None = None,
    report_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root) if repo_root else REPO_ROOT
    case = load_eval_case(case_path)
    playbook_path = root / case["playbook_path"]
    agent_result = run_playbook_agent(playbook_path)

    observed = _observed(agent_result)
    metrics = _metrics(agent_result)
    failures = _evaluate(case, agent_result, observed, metrics)
    result = {
        "case_name": case["name"],
        "description": case.get("description", ""),
        "playbook_path": str(playbook_path),
        "evaluated_at": datetime.now().isoformat(timespec="seconds"),
        "passed": not failures,
        "failures": failures,
        "metrics": metrics,
        "observed": observed,
    }
    if report_path:
        _write_report(result, Path(report_path))
    return result


def _evaluate(
    case: Mapping[str, Any],
    agent_result: Mapping[str, Any],
    observed: Mapping[str, Any],
    metrics: Mapping[str, int],
) -> list[str]:
    expected = case["expected"]
    failures: list[str] = []
    _check_ai_mode(expected, agent_result, failures)
    _check_min_counts(expected, metrics, failures)
    _check_required_items(
        expected.get("required_proposed_tools", []),
        observed["proposed_tools"],
        "required proposed tool",
        failures,
    )
    _check_required_items(
        expected.get("required_preflight_tools", []),
        observed["preflight_tools"],
        "required preflight tool",
        failures,
    )
    _check_forbidden_items(
        expected.get("forbidden_proposed_tools", []),
        observed["proposed_tools"],
        "forbidden proposed tool",
        failures,
    )
    _check_required_items(
        expected.get("required_skill_names", []),
        observed["skill_names"],
        "required skill",
        failures,
    )
    _check_required_items(
        expected.get("required_campaign_names", []),
        observed["campaign_names"],
        "required campaign",
        failures,
    )
    _check_required_items(
        expected.get("required_dnis_numbers", []),
        observed["dnis_numbers"],
        "required DNIS",
        failures,
    )
    _check_ivr_expectations(expected.get("ivr", {}), agent_result, observed, failures)
    _check_plan_contract(agent_result, failures)
    _check_no_xml_content(agent_result, failures)
    return failures


def _observed(agent_result: Mapping[str, Any]) -> dict[str, Any]:
    proposed_plan = list(agent_result.get("proposed_write_plan", []))
    ai_planned_calls = list(agent_result.get("ai_planned_calls", []))
    preflight_plan = list(agent_result.get("preflight_plan", []))
    ivr_preflight_plan = list(agent_result.get("ivr_preflight_plan", []))
    return {
        "ai_mode": agent_result.get("ai_mode"),
        "proposed_tools": [call.get("tool_name") for call in proposed_plan],
        "ai_tools": [call.get("tool_name") for call in ai_planned_calls],
        "preflight_tools": [call.get("tool_name") for call in preflight_plan + ivr_preflight_plan],
        "skill_names": _param_values(ai_planned_calls, "five9_create_skill", "name"),
        "campaign_names": _campaign_names(ai_planned_calls),
        "dnis_numbers": _dnis_numbers(ai_planned_calls),
        "ivr_script_name": (agent_result.get("ivr_requirements") or {}).get("script_name", ""),
        "plan_id": agent_result.get("plan_id", ""),
    }


def _metrics(agent_result: Mapping[str, Any]) -> dict[str, int]:
    summary = agent_result.get("summary") or {}
    return {
        "ai_planned_calls": len(agent_result.get("ai_planned_calls", [])),
        "proposed_write_calls": len(agent_result.get("proposed_write_plan", [])),
        "preflight_calls": len(agent_result.get("preflight_plan", []))
        + len(agent_result.get("ivr_preflight_plan", [])),
        "skills": int(summary.get("skills") or 0),
        "dispositions": int(summary.get("dispositions") or 0),
        "prompts": int(summary.get("prompts") or 0),
        "inbound_campaigns": int(summary.get("inbound_campaigns") or 0),
        "dnis": int(summary.get("dnis") or 0),
        "review_items": len(agent_result.get("review_items", [])),
    }


def _check_ai_mode(
    expected: Mapping[str, Any],
    agent_result: Mapping[str, Any],
    failures: list[str],
) -> None:
    allowed_modes = set(expected.get("ai_modes") or [])
    if allowed_modes and agent_result.get("ai_mode") not in allowed_modes:
        failures.append(
            f"AI mode {agent_result.get('ai_mode')} not in allowed modes {sorted(allowed_modes)}"
        )


def _check_min_counts(
    expected: Mapping[str, Any],
    metrics: Mapping[str, int],
    failures: list[str],
) -> None:
    for name, minimum in (expected.get("min_counts") or {}).items():
        actual = metrics.get(name, 0)
        if actual < int(minimum):
            failures.append(f"Metric {name} was {actual}; expected at least {minimum}")


def _check_required_items(
    required: list[str],
    observed: list[str],
    label: str,
    failures: list[str],
) -> None:
    observed_set = set(observed)
    for item in required:
        if item not in observed_set:
            failures.append(f"Missing {label}: {item}")


def _check_forbidden_items(
    forbidden: list[str],
    observed: list[str],
    label: str,
    failures: list[str],
) -> None:
    observed_set = set(observed)
    for item in forbidden:
        if item in observed_set:
            failures.append(f"Found {label}: {item}")


def _check_ivr_expectations(
    expected_ivr: Mapping[str, Any],
    agent_result: Mapping[str, Any],
    observed: Mapping[str, Any],
    failures: list[str],
) -> None:
    if expected_ivr.get("requires_script_name") and not observed.get("ivr_script_name"):
        failures.append("Missing IVR script_name")
    if expected_ivr.get("requires_create_shell") and "five9_create_ivr_script" not in observed["proposed_tools"]:
        failures.append("Missing IVR script shell create call")
    if expected_ivr.get("forbid_xml_generation"):
        for call in agent_result.get("proposed_write_plan", []):
            if call.get("tool_name") in {"five9_modify_ivr_script", "five9_delete_ivr_script"}:
                failures.append(f"Unsupported IVR script operation proposed: {call.get('tool_name')}")


def _check_plan_contract(agent_result: Mapping[str, Any], failures: list[str]) -> None:
    try:
        validate_agent_executable_plan(agent_result.get("proposed_write_plan", []))
    except Exception as exc:
        failures.append(f"Proposed write plan failed executable schema validation: {exc}")
    if not agent_result.get("plan_id"):
        failures.append("Missing plan_id")


def _check_no_xml_content(value: Any, failures: list[str], path: str = "agent_result") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_XML_KEYS:
                failures.append(f"Forbidden XML key present: {child_path}")
            _check_no_xml_content(child, failures, child_path)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _check_no_xml_content(child, failures, f"{path}[{index}]")
        return
    if isinstance(value, str) and _looks_like_raw_ivr_xml(value):
        failures.append(f"Raw IVR XML content present at {path}")


def _looks_like_raw_ivr_xml(value: str) -> bool:
    stripped = value.strip().lower()
    return stripped.startswith("<ivr") or "<ivrscript" in stripped or "<ivr-script" in stripped


def _param_values(calls: list[Mapping[str, Any]], tool_name: str, param_name: str) -> list[str]:
    return [
        str(call.get("params", {}).get(param_name))
        for call in calls
        if call.get("tool_name") == tool_name and call.get("params", {}).get(param_name)
    ]


def _campaign_names(calls: list[Mapping[str, Any]]) -> list[str]:
    names = _param_values(calls, "five9_create_inbound_campaign", "campaign_name")
    for call in calls:
        params = call.get("params", {})
        if call.get("tool_name") in {
            "five9_add_skills_to_campaign",
            "five9_add_dispositions_to_campaign",
            "five9_add_dnis_to_campaign",
            "five9_set_default_ivr_schedule",
        } and params.get("campaign_name"):
            names.append(str(params["campaign_name"]))
    return _unique(names)


def _dnis_numbers(calls: list[Mapping[str, Any]]) -> list[str]:
    values: list[str] = []
    for call in calls:
        if call.get("tool_name") != "five9_add_dnis_to_campaign":
            continue
        for number in call.get("params", {}).get("dnis", []):
            values.append(str(number))
    return _unique(values)


def _unique(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _write_report(result: Mapping[str, Any], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")


def _require_string(value: Mapping[str, Any], key: str) -> None:
    if not isinstance(value.get(key), str) or not value[key].strip():
        raise ValueError(f"Eval case {key} must be a non-empty string")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CCaaS agent playbook evals.")
    parser.add_argument(
        "--case",
        default=str(REPO_ROOT / "evals" / "cases" / "jacuzzi_playbook_agent_eval.json"),
        help="Path to eval case JSON.",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "evals" / "reports" / "latest_jacuzzi_playbook_agent.json"),
        help="Path to write JSON report.",
    )
    args = parser.parse_args(argv)
    result = run_eval_case(args.case, repo_root=REPO_ROOT, report_path=args.report)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
