from __future__ import annotations

from typing import Any

from ...common.write_common import (
    build_planned_write_result,
    build_write_result,
    clean_params,
    require_live_write,
    require_text,
)


TOOL_NAME = "five9_delete_ivr_script"
SOAP_METHOD = "deleteIVRScript"


def five9_delete_ivr_script(
    name: str,
    mode: str = "dry_run",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    name = require_text(name, "name")
    params = clean_params(name=name)
    if mode == "dry_run":
        return build_planned_write_result(TOOL_NAME, params, SOAP_METHOD)

    require_live_write(mode, approved, client)
    data = client.delete_ivr_script(**params)
    return build_write_result(TOOL_NAME, params, mode="live", result="success", data=data)
