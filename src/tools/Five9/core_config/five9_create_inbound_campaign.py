from __future__ import annotations

from typing import Any

from ..common.write_common import (
    build_planned_write_result,
    build_write_result,
    clean_params,
    require_live_write,
    require_text,
)


TOOL_NAME = "five9_create_inbound_campaign"
SOAP_METHOD = "createInboundCampaign"


def five9_create_inbound_campaign(
    campaign_name: str,
    description: str | None = None,
    max_num_of_lines: int | None = None,
    mode: str = "dry_run",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    campaign_name = require_text(campaign_name, "campaign_name")
    params = clean_params(
        campaign_name=campaign_name,
        description=description,
        max_num_of_lines=max_num_of_lines,
    )
    if mode == "dry_run":
        return build_planned_write_result(TOOL_NAME, params, SOAP_METHOD)

    require_live_write(mode, approved, client)
    data = client.create_inbound_campaign(**params)
    return build_write_result(TOOL_NAME, params, mode="live", result="success", data=data)
