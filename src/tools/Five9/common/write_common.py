from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Mapping


def build_write_result(
    tool_name: str,
    params: Mapping[str, Any],
    mode: str,
    result: str,
    data: Any,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "params": deepcopy(dict(params)),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "result": result,
        "data": deepcopy(data),
    }


def build_planned_write_result(
    tool_name: str,
    params: Mapping[str, Any],
    soap_method: str,
) -> dict[str, Any]:
    return build_write_result(
        tool_name=tool_name,
        params=params,
        mode="dry_run",
        result="planned",
        data={"would_call": soap_method},
    )


def build_write_error_result(
    tool_name: str,
    params: Mapping[str, Any],
    mode: str,
    error: str,
) -> dict[str, Any]:
    result = build_write_result(
        tool_name=tool_name,
        params=params,
        mode=mode,
        result="failed",
        data={},
    )
    result["error"] = error
    return result


def clean_params(**params: Any) -> dict[str, Any]:
    return {
        key: value
        for key, value in params.items()
        if value is not None and value != ""
    }


def require_live_write(mode: str, approved: bool, client: Any | None) -> None:
    if mode not in ("dry_run", "live"):
        raise ValueError("mode must be 'dry_run' or 'live'")
    if mode == "dry_run":
        return
    if approved is not True:
        raise PermissionError("Live Five9 write calls require explicit approval")
    if client is None:
        raise ValueError("Live Five9 write calls require a client")


def require_text(value: str | None, field_name: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{field_name} is required")
    return str(value).strip()


def require_list(values: list[str] | tuple[str, ...] | str | None, field_name: str) -> list[str]:
    if values is None:
        raise ValueError(f"{field_name} is required")
    if isinstance(values, str):
        values = [values]
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    if not cleaned:
        raise ValueError(f"{field_name} is required")
    return cleaned
