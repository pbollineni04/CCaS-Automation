from __future__ import annotations

from typing import Any

from ..common.write_common import (
    build_planned_write_result,
    build_write_result,
    clean_params,
    normalize_five9_disposition_name,
    require_live_write,
)


TOOL_NAME = "five9_create_disposition"
SOAP_METHOD = "createDisposition"


def five9_create_disposition(
    name: str,
    description: str | None = None,
    agent_must_complete_worksheet: bool | None = None,
    agent_must_confirm: bool | None = None,
    reset_attempts_counter: bool | None = None,
    mode: str = "dry_run",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    name = normalize_five9_disposition_name(name)
    params = clean_params(
        name=name,
        description=description,
        agent_must_complete_worksheet=agent_must_complete_worksheet,
        agent_must_confirm=agent_must_confirm,
        reset_attempts_counter=reset_attempts_counter,
    )
    if mode == "dry_run":
        return build_planned_write_result(TOOL_NAME, params, SOAP_METHOD)

    require_live_write(mode, approved, client)
    data = client.create_disposition(**params)
    return build_write_result(TOOL_NAME, params, mode="live", result="success", data=data)
