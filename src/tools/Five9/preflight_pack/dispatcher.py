from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime
from typing import Any, Iterable, Mapping


SAMPLE_FIVE9_INVENTORY: dict[str, list[dict[str, Any]]] = {
    "skills": [
        {
            "name": "English",
            "description": "Language skill for English-speaking callers",
        },
        {
            "name": "Spanish",
            "description": "Language skill for Spanish-speaking callers",
        },
        {
            "name": "Billing Specialist",
            "description": "Skill for billing support calls",
        },
        {
            "name": "Support",
            "description": "Existing support routing skill",
        },
    ],
    "dispositions": [
        {"name": "Sale Completed"},
        {"name": "Billing Resolved"},
        {"name": "Transferred to Support"},
    ],
    "prompts": [
        {
            "name": "Main Greeting",
            "type": "tts",
            "text": (
                "Thank you for calling Acme Health Services. Please listen "
                "carefully as our menu options have changed."
            ),
        },
    ],
    "campaigns": [
        {
            "name": "Acme Main Inbound",
            "type": "inbound",
            "skills": ["English", "Spanish"],
            "dispositions": ["Sale Completed"],
            "dnis": ["800-555-0100"],
        },
        {
            "name": "Legacy Billing Inbound",
            "type": "inbound",
            "skills": ["Billing Specialist"],
            "dispositions": ["Billing Resolved"],
            "dnis": ["800-555-0111"],
        },
    ],
    "dnis": [
        {
            "number": "800-555-0100",
            "assigned_campaign": "Acme Main Inbound",
        },
        {
            "number": "800-555-0111",
            "assigned_campaign": "Legacy Billing Inbound",
        },
        {
            "number": "800-555-0199",
            "assigned_campaign": None,
        },
    ],
}


def build_stub_result(
    tool_name: str,
    params: Mapping[str, Any],
    data: Any,
) -> dict[str, Any]:
    return build_tool_result(tool_name, params, data, mode="stub")


def build_tool_result(
    tool_name: str,
    params: Mapping[str, Any],
    data: Any,
    mode: str,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "params": deepcopy(dict(params)),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "result": "success",
        "data": deepcopy(data),
    }


def build_tool_error_result(
    tool_name: str,
    params: Mapping[str, Any],
    mode: str,
    error: str,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "params": deepcopy(dict(params)),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "result": "failed",
        "data": [],
        "error": error,
    }


def five9_get_skills(
    name_pattern: str | None = None,
    mode: str = "stub",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    params = _clean_params(name_pattern=name_pattern)
    if mode == "stub":
        data = _filter_by_name(SAMPLE_FIVE9_INVENTORY["skills"], name_pattern)
        return build_stub_result("five9_get_skills", params, data)

    _validate_live_request(mode, approved, client)
    return build_tool_result(
        "five9_get_skills",
        params,
        client.get_skills(name_pattern),
        mode="live",
    )


def five9_get_dispositions(
    name_pattern: str | None = None,
    mode: str = "stub",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    params = _clean_params(name_pattern=name_pattern)
    if mode == "stub":
        data = _filter_by_name(SAMPLE_FIVE9_INVENTORY["dispositions"], name_pattern)
        return build_stub_result("five9_get_dispositions", params, data)

    _validate_live_request(mode, approved, client)
    return build_tool_result(
        "five9_get_dispositions",
        params,
        client.get_dispositions(name_pattern),
        mode="live",
    )


def five9_get_prompts(
    name_pattern: str | None = None,
    mode: str = "stub",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    params = _clean_params(name_pattern=name_pattern)
    if mode == "stub":
        data = _filter_by_name(SAMPLE_FIVE9_INVENTORY["prompts"], name_pattern)
        return build_stub_result("five9_get_prompts", params, data)

    _validate_live_request(mode, approved, client)
    data = _filter_by_name(client.get_prompts(), name_pattern)
    return build_tool_result(
        "five9_get_prompts",
        params,
        data,
        mode="live",
    )


def five9_get_campaigns(
    name_pattern: str | None = None,
    campaign_type: str | None = None,
    mode: str = "stub",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    params = _clean_params(name_pattern=name_pattern, campaign_type=campaign_type)
    if mode == "stub":
        data = _filter_by_name(SAMPLE_FIVE9_INVENTORY["campaigns"], name_pattern)
        if campaign_type:
            data = [
                campaign
                for campaign in data
                if campaign.get("type", "").lower() == campaign_type.lower()
            ]
        return build_stub_result("five9_get_campaigns", params, data)

    _validate_live_request(mode, approved, client)
    return build_tool_result(
        "five9_get_campaigns",
        params,
        client.get_campaigns(name_pattern, campaign_type),
        mode="live",
    )


def five9_get_dnis_list(
    select_unassigned: bool = False,
    mode: str = "stub",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    params = _clean_params(select_unassigned=select_unassigned)
    if mode == "stub":
        data = deepcopy(SAMPLE_FIVE9_INVENTORY["dnis"])
        if select_unassigned:
            data = [entry for entry in data if entry["assigned_campaign"] is None]
        return build_stub_result("five9_get_dnis_list", params, data)

    _validate_live_request(mode, approved, client)
    return build_tool_result(
        "five9_get_dnis_list",
        params,
        _normalize_dnis_data(client.get_dnis_list(select_unassigned)),
        mode="live",
    )


def five9_get_campaign_dnis_list(
    campaign_name: str,
    mode: str = "stub",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    params = {"campaign_name": campaign_name}
    if mode == "stub":
        data = [
            entry
            for entry in SAMPLE_FIVE9_INVENTORY["dnis"]
            if entry["assigned_campaign"] == campaign_name
        ]
        return build_stub_result("five9_get_campaign_dnis_list", params, data)

    _validate_live_request(mode, approved, client)
    return build_tool_result(
        "five9_get_campaign_dnis_list",
        params,
        _normalize_dnis_data(
            client.get_campaign_dnis_list(campaign_name),
            assigned_campaign=campaign_name,
        ),
        mode="live",
    )


def compare_desired_to_preflight(
    desired: Mapping[str, Any],
    inventory: Mapping[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    current_inventory = deepcopy(inventory or SAMPLE_FIVE9_INVENTORY)
    comparison: dict[str, Any] = {
        "exists": {},
        "missing": {},
        "conflicts": {},
        "recommended_action": [],
    }

    _compare_named_objects(
        comparison,
        desired.get("skills", []),
        current_inventory["skills"],
        "skills",
        "skill",
    )
    _compare_named_objects(
        comparison,
        desired.get("dispositions", []),
        current_inventory["dispositions"],
        "dispositions",
        "disposition",
    )
    _compare_named_objects(
        comparison,
        desired.get("prompts", []),
        current_inventory["prompts"],
        "prompts",
        "prompt",
    )
    _compare_named_objects(
        comparison,
        desired.get("campaigns", []),
        current_inventory["campaigns"],
        "campaigns",
        "campaign",
    )
    _compare_dnis(
        comparison,
        desired.get("dnis", []),
        current_inventory["dnis"],
    )

    return comparison


def _clean_params(**params: Any) -> dict[str, Any]:
    return {
        key: value
        for key, value in params.items()
        if value is not None and value is not False
    }


def _validate_live_request(
    mode: str,
    approved: bool,
    client: Any | None,
) -> None:
    if mode != "live":
        raise ValueError("mode must be 'stub' or 'live'")
    if approved is not True:
        raise PermissionError("Live Five9 API calls require explicit approval")
    if client is None:
        raise ValueError("A Five9ConfigClient is required for live mode")


def _normalize_dnis_data(
    values: Iterable[Any],
    assigned_campaign: str | None = None,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for value in values:
        if isinstance(value, Mapping):
            number = value.get("number") or value.get("dnis")
            current_campaign = value.get("assigned_campaign", assigned_campaign)
        else:
            number = value
            current_campaign = assigned_campaign

        if number:
            normalized.append(
                {
                    "number": str(number),
                    "assigned_campaign": current_campaign,
                }
            )
    return normalized


def _compile_pattern(name_pattern: str | None) -> re.Pattern[str] | None:
    if not name_pattern:
        return None

    try:
        return re.compile(name_pattern, re.IGNORECASE)
    except re.error:
        return re.compile(re.escape(name_pattern), re.IGNORECASE)


def _filter_by_name(
    items: Iterable[Mapping[str, Any]],
    name_pattern: str | None,
) -> list[dict[str, Any]]:
    pattern = _compile_pattern(name_pattern)
    if pattern is None:
        return deepcopy(list(items))

    return [
        deepcopy(dict(item))
        for item in items
        if pattern.search(str(item.get("name", "")))
    ]


def _name_set(items: Iterable[Mapping[str, Any]]) -> set[str]:
    return {str(item["name"]) for item in items}


def _normalize_names(items: Iterable[Any]) -> list[str]:
    names: list[str] = []
    for item in items:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, Mapping) and item.get("name"):
            names.append(str(item["name"]))
    return names


def _compare_named_objects(
    comparison: dict[str, Any],
    desired_names: Iterable[Any],
    inventory_items: Iterable[Mapping[str, Any]],
    plural_key: str,
    object_type: str,
) -> None:
    existing_names = _name_set(inventory_items)

    for name in _normalize_names(desired_names):
        if name in existing_names:
            comparison["exists"].setdefault(plural_key, []).append(name)
            _add_action(comparison, object_type, name, "skip")
        else:
            comparison["missing"].setdefault(plural_key, []).append(name)
            _add_action(comparison, object_type, name, "create")


def _normalize_dnis_entries(entries: Iterable[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        if isinstance(entry, str):
            normalized.append({"number": entry, "campaign_name": None})
        elif isinstance(entry, Mapping):
            number = entry.get("number") or entry.get("dnis")
            if number:
                normalized.append(
                    {
                        "number": str(number),
                        "campaign_name": entry.get("campaign_name")
                        or entry.get("campaign"),
                    }
                )
    return normalized


def _compare_dnis(
    comparison: dict[str, Any],
    desired_dnis: Iterable[Any],
    inventory_dnis: Iterable[Mapping[str, Any]],
) -> None:
    current_by_number = {
        str(entry["number"]): entry for entry in inventory_dnis if entry.get("number")
    }

    for desired_entry in _normalize_dnis_entries(desired_dnis):
        number = desired_entry["number"]
        requested_campaign = desired_entry["campaign_name"]
        current_entry = current_by_number.get(number)

        if current_entry is None:
            comparison["missing"].setdefault("dnis", []).append(
                {
                    "number": number,
                    "campaign_name": requested_campaign,
                }
            )
            _add_action(comparison, "dnis", number, "create")
            continue

        assigned_campaign = current_entry.get("assigned_campaign")
        if requested_campaign and assigned_campaign and assigned_campaign != requested_campaign:
            comparison["conflicts"].setdefault("dnis", []).append(
                {
                    "number": number,
                    "requested_campaign": requested_campaign,
                    "assigned_campaign": assigned_campaign,
                }
            )
            _add_action(
                comparison,
                "dnis",
                number,
                "review",
                reason=f"Assigned to {assigned_campaign}",
            )
            continue

        if requested_campaign and assigned_campaign is None:
            comparison["missing"].setdefault("dnis", []).append(
                {
                    "number": number,
                    "campaign_name": requested_campaign,
                }
            )
            _add_action(
                comparison,
                "dnis",
                number,
                "create",
                reason="DNIS exists but is not assigned to requested campaign",
            )
            continue

        comparison["exists"].setdefault("dnis", []).append(
            {
                "number": number,
                "campaign_name": assigned_campaign,
            }
        )
        _add_action(comparison, "dnis", number, "skip")


def _add_action(
    comparison: dict[str, Any],
    object_type: str,
    name: str,
    action: str,
    reason: str | None = None,
) -> None:
    entry = {
        "object_type": object_type,
        "name": name,
        "action": action,
    }
    if reason:
        entry["reason"] = reason
    comparison["recommended_action"].append(entry)


__all__ = [
    "SAMPLE_FIVE9_INVENTORY",
    "build_tool_error_result",
    "build_stub_result",
    "build_tool_result",
    "compare_desired_to_preflight",
    "five9_get_campaign_dnis_list",
    "five9_get_campaigns",
    "five9_get_dispositions",
    "five9_get_dnis_list",
    "five9_get_prompts",
    "five9_get_skills",
]
