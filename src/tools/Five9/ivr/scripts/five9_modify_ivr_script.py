from __future__ import annotations

from typing import Any

from ...common.write_common import (
    build_planned_write_result,
    build_write_result,
    clean_params,
    require_live_write,
    require_text,
)


TOOL_NAME = "five9_modify_ivr_script"
SOAP_METHOD = "modifyIVRScript"
_UNSET = object()


def five9_modify_ivr_script(
    name: str,
    description: str | None = None,
    xml_definition: Any = _UNSET,
    mode: str = "dry_run",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    name = require_text(name, "name")
    if xml_definition is _UNSET:
        xml_value = None
    else:
        xml_value = require_text(xml_definition, "xml_definition")

    params = clean_params(
        name=name,
        description=description,
        xml_definition=xml_value,
    )
    if mode == "dry_run":
        return build_planned_write_result(TOOL_NAME, params, SOAP_METHOD)

    require_live_write(mode, approved, client)
    data = client.modify_ivr_script(**params)
    return build_write_result(TOOL_NAME, params, mode="live", result="success", data=data)
