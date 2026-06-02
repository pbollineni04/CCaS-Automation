from __future__ import annotations

from typing import Any

from ..common.write_common import (
    build_planned_write_result,
    build_write_result,
    clean_params,
    normalize_five9_disposition_name,
    require_list,
    require_live_write,
    require_text,
)


TOOL_NAME = "five9_add_dispositions_to_campaign"
SOAP_METHOD = "addDispositionsToCampaign"


def five9_add_dispositions_to_campaign(
    campaign_name: str,
    dispositions: list[str] | str,
    is_skip_preview_disposition: bool | None = None,
    mode: str = "dry_run",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    campaign_name = require_text(campaign_name, "campaign_name")
    disposition_values = list(
        dict.fromkeys(
            normalize_five9_disposition_name(disposition)
            for disposition in require_list(dispositions, "dispositions")
        )
    )
    params = clean_params(
        campaign_name=campaign_name,
        dispositions=disposition_values,
        is_skip_preview_disposition=is_skip_preview_disposition,
    )
    if mode == "dry_run":
        return build_planned_write_result(TOOL_NAME, params, SOAP_METHOD)

    require_live_write(mode, approved, client)
    data = client.add_dispositions_to_campaign(**params)
    return build_write_result(TOOL_NAME, params, mode="live", result="success", data=data)
