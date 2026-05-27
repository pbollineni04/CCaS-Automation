from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from ...preflight_pack.dispatcher import build_tool_result
from ...common.write_common import require_live_write


TOOL_NAME = "five9_get_ivr_scripts"

SAMPLE_IVR_SCRIPTS = [
    {
        "name": "ZZ_TEST_Codex_IVR_Source",
        "description": "Disposable source IVR for XML discovery",
        "xmlDefinition": (
            '<ivr-script><module type="play" name="Greeting"/>'
            '<module type="menu" name="Main Menu"/></ivr-script>'
        ),
    }
]


def five9_get_ivr_scripts(
    name_pattern: str | None = None,
    mode: str = "dry_run",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    params = {"name_pattern": name_pattern} if name_pattern else {}
    if mode == "dry_run":
        return build_tool_result(
            tool_name=TOOL_NAME,
            params=params,
            data=_filter_scripts(name_pattern),
            mode="dry_run",
        )

    require_live_write(mode, approved, client)
    data = client.get_ivr_scripts(name_pattern=name_pattern)
    return build_tool_result(TOOL_NAME, params, data=data, mode="live")


def _filter_scripts(name_pattern: str | None) -> list[dict[str, Any]]:
    scripts = deepcopy(SAMPLE_IVR_SCRIPTS)
    if not name_pattern:
        return scripts
    try:
        pattern = re.compile(name_pattern, re.IGNORECASE)
        return [script for script in scripts if pattern.search(script["name"])]
    except re.error:
        needle = name_pattern.lower()
        return [script for script in scripts if needle in script["name"].lower()]
