from __future__ import annotations

from typing import Any

from ..common.write_common import (
    build_planned_write_result,
    build_write_result,
    clean_params,
    require_live_write,
    require_text,
)


TOOL_NAME = "five9_delete_prompt"
SOAP_METHOD = "deletePrompt"


def five9_delete_prompt(
    prompt_name: str,
    mode: str = "dry_run",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    prompt_name = require_text(prompt_name, "prompt_name")
    params = clean_params(prompt_name=prompt_name)
    if mode == "dry_run":
        return build_planned_write_result(TOOL_NAME, params, SOAP_METHOD)

    require_live_write(mode, approved, client)
    data = client.delete_prompt(**params)
    return build_write_result(TOOL_NAME, params, mode="live", result="success", data=data)
