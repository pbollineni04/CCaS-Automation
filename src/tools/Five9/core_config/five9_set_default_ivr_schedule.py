from __future__ import annotations

from typing import Any

from ..common.write_common import (
    build_planned_write_result,
    build_write_result,
    clean_params,
    require_live_write,
    require_text,
)


TOOL_NAME = "five9_set_default_ivr_schedule"
SOAP_METHOD = "setDefaultIVRSchedule"


def five9_set_default_ivr_schedule(
    campaign_name: str,
    script_name: str,
    params: dict[str, Any] | None = None,
    is_visual_mode_enabled: bool | None = None,
    mode: str = "dry_run",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    campaign_name = require_text(campaign_name, "campaign_name")
    script_name = require_text(script_name, "script_name")
    tool_params = clean_params(
        campaign_name=campaign_name,
        script_name=script_name,
        params=params or None,
        is_visual_mode_enabled=is_visual_mode_enabled,
    )
    if mode == "dry_run":
        return build_planned_write_result(TOOL_NAME, tool_params, SOAP_METHOD)

    require_live_write(mode, approved, client)
    data = client.set_default_ivr_schedule(**tool_params)
    return build_write_result(TOOL_NAME, tool_params, mode="live", result="success", data=data)
