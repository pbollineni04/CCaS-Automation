from __future__ import annotations

from typing import Any, Callable

from .five9_modify_disposition import five9_modify_disposition
from .five9_modify_inbound_campaign import five9_modify_inbound_campaign
from .five9_modify_prompt_tts import five9_modify_prompt_tts
from .five9_modify_skill import five9_modify_skill
from ..common.write_common import build_write_error_result


ToolFunc = Callable[..., dict[str, Any]]


_TOOL_REGISTRY: dict[str, ToolFunc] = {
    "five9_modify_skill": five9_modify_skill,
    "five9_modify_disposition": five9_modify_disposition,
    "five9_modify_prompt_tts": five9_modify_prompt_tts,
    "five9_modify_inbound_campaign": five9_modify_inbound_campaign,
}

ALLOWED_MODIFY_TOOL_NAMES = list(_TOOL_REGISTRY.keys())


def execute_modify_plan(
    approved: bool,
    planned_calls: list[dict[str, Any]],
    mode: str = "dry_run",
    client: Any | None = None,
) -> list[dict[str, Any]]:
    if mode not in ("dry_run", "live"):
        raise ValueError("mode must be 'dry_run' or 'live'")
    if mode == "live" and approved is not True:
        raise PermissionError("Live Five9 modify calls require explicit approval")

    results: list[dict[str, Any]] = []
    for call in planned_calls:
        tool_name = call.get("tool_name")
        params = call.get("params", {})
        if tool_name not in _TOOL_REGISTRY:
            raise ValueError(f"Unknown Five9 modify tool: {tool_name}")
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
    "ALLOWED_MODIFY_TOOL_NAMES",
    "execute_modify_plan",
]
