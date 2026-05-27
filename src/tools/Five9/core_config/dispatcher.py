from __future__ import annotations

from typing import Any, Callable

from .five9_add_dispositions_to_campaign import five9_add_dispositions_to_campaign
from .five9_add_dnis_to_campaign import five9_add_dnis_to_campaign
from .five9_add_prompt_tts import five9_add_prompt_tts
from .five9_add_skills_to_campaign import five9_add_skills_to_campaign
from .five9_create_disposition import five9_create_disposition
from .five9_create_inbound_campaign import five9_create_inbound_campaign
from .five9_create_skill import five9_create_skill
from .five9_set_default_ivr_schedule import five9_set_default_ivr_schedule
from ..common.write_common import build_write_error_result


ToolFunc = Callable[..., dict[str, Any]]


_TOOL_REGISTRY: dict[str, ToolFunc] = {
    "five9_create_skill": five9_create_skill,
    "five9_create_disposition": five9_create_disposition,
    "five9_add_prompt_tts": five9_add_prompt_tts,
    "five9_create_inbound_campaign": five9_create_inbound_campaign,
    "five9_add_dnis_to_campaign": five9_add_dnis_to_campaign,
    "five9_add_skills_to_campaign": five9_add_skills_to_campaign,
    "five9_add_dispositions_to_campaign": five9_add_dispositions_to_campaign,
    "five9_set_default_ivr_schedule": five9_set_default_ivr_schedule,
}

ALLOWED_CORE_WRITE_TOOL_NAMES = list(_TOOL_REGISTRY.keys())


def execute_core_write_plan(
    approved: bool,
    planned_calls: list[dict[str, Any]],
    mode: str = "dry_run",
    client: Any | None = None,
) -> list[dict[str, Any]]:
    if mode not in ("dry_run", "live"):
        raise ValueError("mode must be 'dry_run' or 'live'")
    if mode == "live" and approved is not True:
        raise PermissionError("Live Five9 write calls require explicit approval")

    results: list[dict[str, Any]] = []
    for call in planned_calls:
        tool_name = call.get("tool_name")
        params = call.get("params", {})
        if tool_name not in _TOOL_REGISTRY:
            raise ValueError(f"Unknown Five9 core write tool: {tool_name}")
        if not isinstance(params, dict):
            raise ValueError(f"params for {tool_name} must be an object")

        try:
            result = _TOOL_REGISTRY[tool_name](
                mode=mode,
                approved=approved,
                client=client,
                **params,
            )
        except Exception as e:
            result = build_write_error_result(
                tool_name=tool_name,
                params=params,
                mode=mode,
                error=str(e),
            )
            results.append(result)
            break

        results.append(result)

    return results


__all__ = [
    "ALLOWED_CORE_WRITE_TOOL_NAMES",
    "execute_core_write_plan",
]
