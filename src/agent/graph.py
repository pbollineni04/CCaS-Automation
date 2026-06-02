from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .claude_client import interpret_playbook_with_llm
from .planner import (
    build_agent_preflight_plan,
    build_agent_write_plan,
    build_ivr_preflight_plan,
    build_requirement_summary,
    compare_agent_preflight,
    execute_agent_preflight_plan,
    plan_fingerprint,
)
from .playbook_parser import parse_playbook
from .schemas import (
    planned_calls_to_playbook_entities,
    validate_agent_plan_response,
    validate_ivr_requirements,
    validate_ivr_script_plan,
    validate_planned_calls,
)


AGENT_NODES = [
    "parse_playbook",
    "interpret_with_ai",
    "validate_planned_calls",
    "build_preflight_plan",
    "compare_preflight",
    "build_write_plan",
    "await_approval",
    "execute",
]


def run_playbook_agent(
    playbook_path: str | Path,
    *,
    ai_provider: str = "anthropic",
    api_key: str | None = None,
    model: str | None = None,
    session: Any | None = None,
    preflight_mode: str = "stub",
    preflight_approved: bool = False,
    preflight_client: Any | None = None,
) -> dict[str, Any]:
    if preflight_mode not in {"stub", "live"}:
        raise ValueError("preflight_mode must be 'stub' or 'live'")
    state: dict[str, Any] = {
        "playbook_path": playbook_path,
        "status": "planning",
        "preflight_mode": preflight_mode,
        "preflight_approved": preflight_approved,
        "preflight_client": preflight_client,
    }
    for node in _node_pipeline(
        ai_provider=ai_provider,
        api_key=api_key,
        model=model,
        session=session,
    ):
        state = node(state)
    return state


def _node_pipeline(
    *,
    ai_provider: str,
    api_key: str | None,
    model: str | None,
    session: Any | None,
) -> list[Callable[[dict[str, Any]], dict[str, Any]]]:
    return [
        _parse_playbook,
        lambda state: _interpret_with_ai(
            state,
            ai_provider=ai_provider,
            api_key=api_key,
            model=model,
            session=session,
        ),
        _validate_planned_calls_node,
        _build_preflight,
        _compare_preflight,
        _build_write_plan,
        _await_approval,
    ]


def _parse_playbook(state: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_playbook(state["playbook_path"])
    return {**state, "parsed_playbook": parsed}


def _interpret_with_ai(
    state: dict[str, Any],
    *,
    ai_provider: str,
    api_key: str | None,
    model: str | None,
    session: Any | None,
) -> dict[str, Any]:
    interpretation = interpret_playbook_with_llm(
        state["parsed_playbook"],
        provider=ai_provider,
        api_key=api_key,
        model=model,
        session=session,
    )
    return {
        **state,
        "ai_mode": interpretation["ai_mode"],
        "model": interpretation.get("model"),
        "agent_plan": interpretation["agent_plan"],
        "ai_planned_calls": interpretation["planned_calls"],
        "ivr_requirements": interpretation["agent_plan"].get("ivr_requirements", {}),
        "ivr_script_plan": interpretation["agent_plan"].get("ivr_script_plan", []),
        "review_items": list(interpretation.get("review_items", [])),
    }


def _validate_planned_calls_node(state: dict[str, Any]) -> dict[str, Any]:
    agent_plan = validate_agent_plan_response(state["agent_plan"])
    return {
        **state,
        "agent_plan": agent_plan,
        "ai_planned_calls": validate_planned_calls(agent_plan["planned_calls"]),
        "ivr_requirements": validate_ivr_requirements(agent_plan.get("ivr_requirements", {})),
        "ivr_script_plan": validate_ivr_script_plan(agent_plan.get("ivr_script_plan", [])),
    }


def _build_preflight(state: dict[str, Any]) -> dict[str, Any]:
    return {
        **state,
        "requirements": build_requirement_summary(state["ai_planned_calls"]),
        "preflight_plan": build_agent_preflight_plan(state["ai_planned_calls"]),
        "ivr_preflight_plan": build_ivr_preflight_plan(state["ivr_requirements"]),
    }


def _compare_preflight(state: dict[str, Any]) -> dict[str, Any]:
    preflight_results, inventory = execute_agent_preflight_plan(
        state["preflight_plan"],
        mode=state.get("preflight_mode", "stub"),
        approved=bool(state.get("preflight_approved")),
        client=state.get("preflight_client"),
    )
    return {
        **state,
        "preflight_results": preflight_results,
        "preflight_inventory": inventory,
        "comparison": compare_agent_preflight(state["ai_planned_calls"], inventory=inventory),
        "preflight_live": state.get("preflight_mode") == "live",
    }


def _build_write_plan(state: dict[str, Any]) -> dict[str, Any]:
    write_plan, write_actions, review_items = build_agent_write_plan(
        state["ai_planned_calls"],
        state["comparison"],
    )
    ivr_script_plan = validate_ivr_script_plan(state.get("ivr_script_plan", []))
    combined_write_plan = ivr_script_plan + write_plan
    merged_review_items = list(state.get("review_items", [])) + review_items
    planned_entities = planned_calls_to_playbook_entities(state["ai_planned_calls"])
    return {
        **state,
        "proposed_write_plan": combined_write_plan,
        "core_write_plan": write_plan,
        "proposed_ivr_script_plan": ivr_script_plan,
        "write_actions": write_actions,
        "review_items": merged_review_items,
        "ivr_requirements": state["ivr_requirements"],
        "ivr_preflight_plan": list(state.get("ivr_preflight_plan", [])),
        "deferred_items": list(state["agent_plan"].get("deferred_items", [])),
        "plan_id": plan_fingerprint(combined_write_plan),
        "summary": {
            "skills": len(planned_entities.get("skills", [])),
            "dispositions": len(planned_entities.get("dispositions", [])),
            "prompts": len(planned_entities.get("prompts", [])),
            "inbound_campaigns": len(planned_entities.get("inbound_campaigns", [])),
            "dnis": len(planned_entities.get("dnis", [])),
            "ai_planned_calls": len(state["ai_planned_calls"]),
            "preflight_calls": len(state.get("preflight_plan", [])),
            "preflight_result_calls": len(state.get("preflight_results", [])),
            "preflight_live": state.get("preflight_live", False),
            "ivr_preflight_calls": len(state.get("ivr_preflight_plan", [])),
            "ivr_script_create_calls": len(ivr_script_plan),
            "proposed_write_calls": len(combined_write_plan),
            "review_items": len(merged_review_items),
            "includes_ivr_scripts": False,
        },
    }


def _await_approval(state: dict[str, Any]) -> dict[str, Any]:
    output = {**state, "status": "awaiting_approval", "agent_nodes": list(AGENT_NODES)}
    output.pop("preflight_client", None)
    return output


__all__ = ["AGENT_NODES", "run_playbook_agent"]
