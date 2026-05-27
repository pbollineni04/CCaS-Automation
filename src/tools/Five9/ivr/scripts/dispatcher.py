from __future__ import annotations

import re
from typing import Any, Callable

from .five9_create_ivr_script import five9_create_ivr_script
from .five9_delete_ivr_script import five9_delete_ivr_script
from .five9_get_ivr_scripts import five9_get_ivr_scripts
from .five9_modify_ivr_script import five9_modify_ivr_script
from ...common.write_common import build_write_error_result


ToolFunc = Callable[..., dict[str, Any]]


_TOOL_REGISTRY: dict[str, ToolFunc] = {
    "five9_get_ivr_scripts": five9_get_ivr_scripts,
    "five9_create_ivr_script": five9_create_ivr_script,
    "five9_modify_ivr_script": five9_modify_ivr_script,
    "five9_delete_ivr_script": five9_delete_ivr_script,
}

ALLOWED_IVR_SCRIPT_TOOL_NAMES = list(_TOOL_REGISTRY.keys())


def execute_ivr_script_plan(
    approved: bool,
    planned_calls: list[dict[str, Any]],
    mode: str = "dry_run",
    client: Any | None = None,
) -> list[dict[str, Any]]:
    if mode not in ("dry_run", "live"):
        raise ValueError("mode must be 'dry_run' or 'live'")
    if mode == "live" and approved is not True:
        raise PermissionError("Live Five9 IVR script calls require explicit approval")

    results: list[dict[str, Any]] = []
    for call in planned_calls:
        tool_name = call.get("tool_name")
        params = call.get("params", {})
        if tool_name not in _TOOL_REGISTRY:
            raise ValueError(f"Unknown Five9 IVR script tool: {tool_name}")
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


def execute_ivr_script_upsert(
    approved: bool,
    name: str,
    xml_definition: str,
    description: str | None = None,
    mode: str = "dry_run",
    client: Any | None = None,
) -> list[dict[str, Any]]:
    if mode not in ("dry_run", "live"):
        raise ValueError("mode must be 'dry_run' or 'live'")
    if not name or not str(name).strip():
        raise ValueError("name is required")
    if not xml_definition or not str(xml_definition).strip():
        raise ValueError("xml_definition is required")
    if mode == "live" and approved is not True:
        raise PermissionError("Live Five9 IVR script calls require explicit approval")
    if mode == "live" and client is None:
        raise ValueError("client is required for live Five9 IVR script calls")

    clean_name = str(name).strip()
    results: list[dict[str, Any]] = []

    read_result = five9_get_ivr_scripts(
        name_pattern=f"^{re.escape(clean_name)}$",
        mode=mode,
        approved=approved,
        client=client,
    )
    results.append(read_result)
    if read_result.get("result") == "failed":
        return results

    exists = _script_exists(read_result.get("data", []), clean_name)
    if not exists:
        create_result = five9_create_ivr_script(
            name=clean_name,
            mode=mode,
            approved=approved,
            client=client,
        )
        results.append(create_result)
        if create_result.get("result") == "failed":
            return results

    modify_result = five9_modify_ivr_script(
        name=clean_name,
        description=description,
        xml_definition=xml_definition,
        mode=mode,
        approved=approved,
        client=client,
    )
    results.append(modify_result)
    return results


def _script_exists(scripts: Any, name: str) -> bool:
    if not isinstance(scripts, list):
        return False
    for script in scripts:
        if isinstance(script, dict) and str(script.get("name", "")).strip() == name:
            return True
        if str(script).strip() == name:
            return True
    return False


__all__ = [
    "ALLOWED_IVR_SCRIPT_TOOL_NAMES",
    "execute_ivr_script_plan",
    "execute_ivr_script_upsert",
]
