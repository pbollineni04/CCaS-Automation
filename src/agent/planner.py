from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from .playbook_flow import build_requirement_groups
from .schemas import (
    planned_calls_to_playbook_entities,
    validate_planned_calls,
)
from src.tools.Five9.preflight_pack.dispatcher import compare_desired_to_preflight
from src.tools.Five9.preflight_pack import dispatcher as five9_preflight


def build_agent_preflight_plan(planned_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validate_planned_calls(planned_calls)
    return [
        {"tool_name": "five9_get_skills", "params": {}},
        {"tool_name": "five9_get_dispositions", "params": {}},
        {"tool_name": "five9_get_prompts", "params": {}},
        {"tool_name": "five9_get_campaigns", "params": {"campaign_type": "inbound"}},
        {"tool_name": "five9_get_dnis_list", "params": {}},
    ]


def compare_agent_preflight(
    planned_calls: list[dict[str, Any]],
    inventory: Mapping[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    entities = planned_calls_to_playbook_entities(planned_calls)
    return compare_desired_to_preflight(
        {
            "skills": entities["skills"],
            "dispositions": entities["dispositions"],
            "prompts": [{"name": prompt["prompt_name"]} for prompt in entities["prompts"]],
            "campaigns": [{"name": campaign["campaign_name"]} for campaign in entities["inbound_campaigns"]],
            "dnis": entities["dnis"],
        },
        inventory=inventory,
    )


def execute_agent_preflight_plan(
    preflight_plan: list[dict[str, Any]],
    *,
    mode: str = "stub",
    approved: bool = False,
    client: Any | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    if mode not in {"stub", "live"}:
        raise ValueError("preflight mode must be 'stub' or 'live'")

    results: list[dict[str, Any]] = []
    inventory: dict[str, list[dict[str, Any]]] = {
        "skills": [],
        "dispositions": [],
        "prompts": [],
        "campaigns": [],
        "dnis": [],
    }

    for call in preflight_plan:
        tool_name = call.get("tool_name")
        params = dict(call.get("params") or {})
        result = _execute_preflight_call(
            tool_name=str(tool_name),
            params=params,
            mode=mode,
            approved=approved,
            client=client,
        )
        results.append(result)
        _merge_preflight_result(inventory, result)

    return results, inventory


def build_agent_write_plan(
    planned_calls: list[dict[str, Any]],
    comparison: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    planned_calls = validate_planned_calls(planned_calls)
    missing = comparison.get("missing", {})
    conflicts = comparison.get("conflicts", {})
    conflict_dnis_numbers = {
        str(item.get("number"))
        for item in conflicts.get("dnis", [])
        if isinstance(item, Mapping) and item.get("number")
    }

    write_plan = [
        call
        for call in planned_calls
        if _planned_call_should_run(call, missing, conflict_dnis_numbers)
    ]
    assert_safe_write_plan(write_plan)
    write_actions = [
        deepcopy(action)
        for action in comparison.get("recommended_action", [])
        if action.get("action") in {"create", "skip"}
    ]
    review_items = _review_items_from_conflicts(conflicts)
    return write_plan, write_actions, review_items


def build_requirement_summary(planned_calls: list[dict[str, Any]]) -> dict[str, list[str]]:
    return build_requirement_groups(planned_calls_to_playbook_entities(planned_calls))


def build_ivr_preflight_plan(ivr_requirements: Mapping[str, Any]) -> list[dict[str, Any]]:
    script_name = str(ivr_requirements.get("script_name") or "").strip()
    if not script_name:
        return []
    return [
        {
            "tool_name": "five9_get_ivr_scripts",
            "params": {"name_pattern": script_name},
        }
    ]


def _execute_preflight_call(
    *,
    tool_name: str,
    params: Mapping[str, Any],
    mode: str,
    approved: bool,
    client: Any | None,
) -> dict[str, Any]:
    if tool_name == "five9_get_skills":
        return five9_preflight.five9_get_skills(
            name_pattern=params.get("name_pattern"),
            mode=mode,
            approved=approved,
            client=client,
        )
    if tool_name == "five9_get_dispositions":
        return five9_preflight.five9_get_dispositions(
            name_pattern=params.get("name_pattern"),
            mode=mode,
            approved=approved,
            client=client,
        )
    if tool_name == "five9_get_prompts":
        return five9_preflight.five9_get_prompts(
            name_pattern=params.get("name_pattern"),
            mode=mode,
            approved=approved,
            client=client,
        )
    if tool_name == "five9_get_campaigns":
        return five9_preflight.five9_get_campaigns(
            name_pattern=params.get("name_pattern"),
            campaign_type=params.get("campaign_type"),
            mode=mode,
            approved=approved,
            client=client,
        )
    if tool_name == "five9_get_dnis_list":
        return five9_preflight.five9_get_dnis_list(
            select_unassigned=bool(params.get("select_unassigned", False)),
            mode=mode,
            approved=approved,
            client=client,
        )
    if tool_name == "five9_get_campaign_dnis_list":
        return five9_preflight.five9_get_campaign_dnis_list(
            campaign_name=str(params["campaign_name"]),
            mode=mode,
            approved=approved,
            client=client,
        )
    raise ValueError(f"Unsupported agent preflight tool: {tool_name}")


def _merge_preflight_result(
    inventory: dict[str, list[dict[str, Any]]],
    result: Mapping[str, Any],
) -> None:
    if result.get("result") != "success":
        raise ValueError(f"{result.get('tool_name')} failed: {result.get('error')}")
    data = result.get("data") or []
    if not isinstance(data, list):
        return
    tool_name = result.get("tool_name")
    if tool_name == "five9_get_skills":
        inventory["skills"] = _dedupe_by_key(inventory["skills"] + data, "name")
    elif tool_name == "five9_get_dispositions":
        inventory["dispositions"] = _dedupe_by_key(inventory["dispositions"] + data, "name")
    elif tool_name == "five9_get_prompts":
        inventory["prompts"] = _dedupe_by_key(inventory["prompts"] + data, "name")
    elif tool_name == "five9_get_campaigns":
        inventory["campaigns"] = _dedupe_by_key(inventory["campaigns"] + data, "name")
    elif tool_name in {"five9_get_dnis_list", "five9_get_campaign_dnis_list"}:
        inventory["dnis"] = _dedupe_by_key(inventory["dnis"] + data, "number")


def _dedupe_by_key(values: list[Any], key: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for value in values:
        if not isinstance(value, Mapping):
            continue
        item = dict(value)
        identity = str(item.get(key) or "")
        if not identity or identity in seen:
            continue
        seen.add(identity)
        output.append(item)
    return output


def plan_fingerprint(planned_calls: list[dict[str, Any]]) -> str:
    payload = json.dumps(planned_calls, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()[:24]


def plans_match(expected: list[dict[str, Any]], submitted: list[dict[str, Any]]) -> bool:
    return _canonical_plan(expected) == _canonical_plan(submitted)


def assert_safe_write_plan(planned_calls: list[dict[str, Any]]) -> None:
    sensitive_keys = {
        "name",
        "campaign_name",
        "skills",
        "dispositions",
        "dnis",
        "prompt_name",
        "text",
    }
    for call_index, call in enumerate(planned_calls):
        params = call.get("params", {})
        if not isinstance(params, Mapping):
            raise ValueError(f"planned_calls[{call_index}].params must be an object")
        _assert_safe_param_values(params, f"planned_calls[{call_index}].params", sensitive_keys)


def _canonical_plan(plan: list[dict[str, Any]]) -> str:
    return json.dumps(plan, sort_keys=True, separators=(",", ":"))


def _assert_safe_param_values(value: Any, path: str, sensitive_keys: set[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in sensitive_keys:
                _assert_safe_param_values(child, child_path, sensitive_keys)
            elif isinstance(child, (Mapping, list)):
                _assert_safe_param_values(child, child_path, sensitive_keys)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _assert_safe_param_values(child, f"{path}[{index}]", sensitive_keys)
        return
    if isinstance(value, str) and _looks_like_serialized_object(value):
        raise ValueError(f"{path} looks like serialized object data")


def _looks_like_serialized_object(text: str) -> bool:
    stripped = text.strip()
    if "{" in stripped or "}" in stripped:
        return True
    lowered = stripped.lower()
    return any(token in lowered for token in ("'name'", '"name"', "'number'", '"number"'))


def _planned_call_should_run(
    call: Mapping[str, Any],
    missing: Mapping[str, Any],
    conflict_dnis_numbers: set[str],
) -> bool:
    tool_name = call.get("tool_name")
    params = call.get("params", {})
    if tool_name == "five9_create_skill":
        return str(params.get("name")) in {str(item) for item in missing.get("skills", [])}
    if tool_name == "five9_create_disposition":
        return str(params.get("name")) in {str(item) for item in missing.get("dispositions", [])}
    if tool_name == "five9_add_prompt_tts":
        return str(params.get("prompt_name")) in {str(item) for item in missing.get("prompts", [])}
    if tool_name == "five9_create_inbound_campaign":
        return str(params.get("campaign_name")) in {str(item) for item in missing.get("campaigns", [])}
    if tool_name in {
        "five9_add_skills_to_campaign",
        "five9_add_dispositions_to_campaign",
        "five9_set_default_ivr_schedule",
    }:
        return str(params.get("campaign_name")) in {str(item) for item in missing.get("campaigns", [])}
    if tool_name == "five9_add_dnis_to_campaign":
        campaign_name = str(params.get("campaign_name") or "")
        if any(str(number) in conflict_dnis_numbers for number in params.get("dnis", [])):
            return False
        for number in params.get("dnis", []):
            if _dnis_is_missing({"number": str(number), "campaign_name": campaign_name}, missing.get("dnis", [])):
                return True
        return False
    return False


def _dnis_is_missing(entry: Mapping[str, Any], missing_entries: list[Any]) -> bool:
    number = str(entry.get("number") or "")
    campaign_name = str(entry.get("campaign_name") or "")
    for missing in missing_entries:
        if isinstance(missing, Mapping):
            if str(missing.get("number") or "") == number and str(missing.get("campaign_name") or "") == campaign_name:
                return True
        elif str(missing) == number:
            return True
    return False


def _review_items_from_conflicts(conflicts: Mapping[str, Any]) -> list[dict[str, str]]:
    review_items: list[dict[str, str]] = []
    for item in conflicts.get("dnis", []):
        if not isinstance(item, Mapping):
            continue
        review_items.append(
            {
                "severity": "warning",
                "message": (
                    f"DNIS {item.get('number')} is assigned to "
                    f"{item.get('assigned_campaign')} but playbook requests "
                    f"{item.get('requested_campaign')}."
                ),
            }
        )
    return review_items


__all__ = [
    "build_agent_preflight_plan",
    "build_ivr_preflight_plan",
    "build_agent_write_plan",
    "build_requirement_summary",
    "compare_agent_preflight",
    "execute_agent_preflight_plan",
    "assert_safe_write_plan",
    "plan_fingerprint",
    "plans_match",
]
