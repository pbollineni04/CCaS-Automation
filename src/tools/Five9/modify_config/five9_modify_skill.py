from __future__ import annotations

from typing import Any

from ..common.write_common import (
    build_planned_write_result,
    build_write_result,
    clean_params,
    require_live_write,
    require_text,
)


TOOL_NAME = "five9_modify_skill"
SOAP_METHOD = "modifySkill"


def five9_modify_skill(
    skill_name: str,
    description: str | None = None,
    route_voice_mails: bool | None = None,
    message_of_the_day: str | None = None,
    mode: str = "dry_run",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    skill_name = require_text(skill_name, "skill_name")
    params = clean_params(
        skill_name=skill_name,
        description=description,
        route_voice_mails=route_voice_mails,
        message_of_the_day=message_of_the_day,
    )
    if mode == "dry_run":
        return build_planned_write_result(TOOL_NAME, params, SOAP_METHOD)

    require_live_write(mode, approved, client)
    data = client.modify_skill(**params)
    return build_write_result(TOOL_NAME, params, mode="live", result="success", data=data)
