from __future__ import annotations

from typing import Any

from ..common.write_common import (
    build_planned_write_result,
    build_write_result,
    clean_params,
    require_live_write,
    require_text,
)


TOOL_NAME = "five9_add_prompt_tts"
SOAP_METHOD = "addPromptTTS"


def five9_add_prompt_tts(
    prompt_name: str,
    text: str,
    description: str | None = None,
    voice: str | None = None,
    language: str | None = None,
    mode: str = "dry_run",
    approved: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    prompt_name = require_text(prompt_name, "prompt_name")
    text = require_text(text, "text")
    params = clean_params(
        prompt_name=prompt_name,
        text=text,
        description=description,
        voice=voice,
        language=language,
    )
    if mode == "dry_run":
        return build_planned_write_result(TOOL_NAME, params, SOAP_METHOD)

    require_live_write(mode, approved, client)
    data = client.add_prompt_tts(**params)
    return build_write_result(TOOL_NAME, params, mode="live", result="success", data=data)
