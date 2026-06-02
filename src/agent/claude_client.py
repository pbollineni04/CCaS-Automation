from __future__ import annotations

import json
import os
import re
from typing import Any, Mapping

import requests

from .schemas import (
    ALLOWED_CORE_WRITE_TOOL_NAMES,
    build_fallback_desired_config,
    planned_calls_contract_text,
    validate_agent_plan_response,
)
from .playbook_flow import build_core_write_plan


ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
OPENAI_ENDPOINT = "https://api.openai.com/v1/responses"
GEMINI_ENDPOINT_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
DEFAULT_OPENAI_MODEL = "gpt-5.2"
DEFAULT_GEMINI_MODEL = "gemini-2.5-pro"
ANTHROPIC_VERSION = "2023-06-01"


def interpret_playbook_with_llm(
    parsed_playbook: Mapping[str, Any],
    provider: str = "anthropic",
    api_key: str | None = None,
    model: str | None = None,
    session: Any | None = None,
) -> dict[str, Any]:
    normalized_provider = _normalize_provider(provider)
    if normalized_provider == "anthropic":
        return interpret_playbook_with_claude(
            parsed_playbook,
            api_key=api_key,
            model=model,
            session=session,
        )
    if normalized_provider == "openai":
        return _interpret_with_openai(parsed_playbook, api_key, model, session)
    if normalized_provider == "gemini":
        return _interpret_with_gemini(parsed_playbook, api_key, model, session)

    fallback = build_fallback_agent_plan_response(parsed_playbook)
    return {
        "ai_mode": "fallback",
        "model": None,
        "agent_plan": fallback,
        "planned_calls": fallback["planned_calls"],
        "review_items": [
            {
                "severity": "warning",
                "message": f"Unsupported AI provider '{provider}'; deterministic fallback was used.",
            }
        ],
    }


def interpret_playbook_with_claude(
    parsed_playbook: Mapping[str, Any],
    api_key: str | None = None,
    model: str | None = None,
    session: Any | None = None,
) -> dict[str, Any]:
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    fallback = build_fallback_agent_plan_response(parsed_playbook)
    if not key:
        return {
            "ai_mode": "fallback",
            "model": None,
            "agent_plan": fallback,
            "planned_calls": fallback["planned_calls"],
            "review_items": [
                {
                    "severity": "info",
                    "message": "ANTHROPIC_API_KEY is not set; deterministic fallback was used.",
                }
            ],
        }

    selected_model = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
    http = session or requests.Session()
    try:
        response = http.post(
            ANTHROPIC_ENDPOINT,
            headers={
                "x-api-key": key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": selected_model,
                "max_tokens": 5000,
                "temperature": 0,
                "system": _system_prompt(),
                "messages": [
                    {
                        "role": "user",
                        "content": _user_prompt(parsed_playbook),
                    }
                ],
            },
            timeout=90,
        )
        response.raise_for_status()
        agent_plan = validate_agent_plan_response(_extract_json_object(response.json()))
        return {
            "ai_mode": "claude",
            "model": selected_model,
            "agent_plan": agent_plan,
            "planned_calls": agent_plan["planned_calls"],
            "review_items": [],
        }
    except Exception as exc:
        return {
            "ai_mode": "fallback",
            "model": selected_model,
            "agent_plan": fallback,
            "planned_calls": fallback["planned_calls"],
            "review_items": [
                {
                    "severity": "warning",
                    "message": (
                        "Claude interpretation failed; deterministic fallback was used: "
                        f"{_sanitize_exception(exc)}"
                    ),
                }
            ],
        }


def _interpret_with_openai(
    parsed_playbook: Mapping[str, Any],
    api_key: str | None,
    model: str | None,
    session: Any | None,
) -> dict[str, Any]:
    key = api_key or os.environ.get("OPENAI_API_KEY")
    fallback = build_fallback_agent_plan_response(parsed_playbook)
    if not key:
        return _missing_key_fallback("OPENAI_API_KEY", fallback)

    selected_model = model or os.environ.get("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
    http = session or requests.Session()
    try:
        response = http.post(
            OPENAI_ENDPOINT,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": selected_model,
                "instructions": _system_prompt(),
                "input": _user_prompt(parsed_playbook),
                "max_output_tokens": 5000,
            },
            timeout=90,
        )
        response.raise_for_status()
        agent_plan = validate_agent_plan_response(_extract_json_object_from_text(_extract_openai_text(response.json())))
        return {
            "ai_mode": "openai",
            "model": selected_model,
            "agent_plan": agent_plan,
            "planned_calls": agent_plan["planned_calls"],
            "review_items": [],
        }
    except Exception as exc:
        return _provider_failure_fallback("OpenAI", selected_model, fallback, exc)


def _interpret_with_gemini(
    parsed_playbook: Mapping[str, Any],
    api_key: str | None,
    model: str | None,
    session: Any | None,
) -> dict[str, Any]:
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    fallback = build_fallback_agent_plan_response(parsed_playbook)
    if not key:
        return _missing_key_fallback("GEMINI_API_KEY", fallback)

    selected_model = model or os.environ.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    http = session or requests.Session()
    try:
        response = http.post(
            GEMINI_ENDPOINT_TEMPLATE.format(model=selected_model),
            params={"key": key},
            headers={"Content-Type": "application/json"},
            json={
                "systemInstruction": {"parts": [{"text": _system_prompt()}]},
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": _user_prompt(parsed_playbook)}],
                    }
                ],
                "generationConfig": {
                    "temperature": 0,
                    "maxOutputTokens": 5000,
                },
            },
            timeout=90,
        )
        response.raise_for_status()
        agent_plan = validate_agent_plan_response(_extract_json_object_from_text(_extract_gemini_text(response.json())))
        return {
            "ai_mode": "gemini",
            "model": selected_model,
            "agent_plan": agent_plan,
            "planned_calls": agent_plan["planned_calls"],
            "review_items": [],
        }
    except Exception as exc:
        return _provider_failure_fallback("Gemini", selected_model, fallback, exc)


def _system_prompt() -> str:
    return (
        "You are a CCaaS implementation planner. Normalize the parsed playbook into "
        "the required Five9 API-ready planned call object.\n\n"
        f"{planned_calls_contract_text()}"
    )


def _user_prompt(parsed_playbook: Mapping[str, Any]) -> str:
    compact = {
        "source": parsed_playbook.get("source"),
        "entities": parsed_playbook.get("entities"),
        "ivr_requirements": parsed_playbook.get("ivr_requirements"),
        "requirements": parsed_playbook.get("requirements"),
        "deferred": parsed_playbook.get("deferred"),
    }
    return json.dumps(compact, ensure_ascii=False)


def _extract_json_object(payload: Mapping[str, Any]) -> dict[str, Any]:
    text_parts = [
        item.get("text", "")
        for item in payload.get("content", [])
        if isinstance(item, Mapping) and item.get("type") == "text"
    ]
    text = "\n".join(text_parts).strip()
    if not text:
        raise ValueError("Claude response did not include text content")

    return _extract_json_object_from_text(text)


def _extract_json_object_from_text(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("LLM response JSON must be an object")
    return value


def _extract_openai_text(payload: Mapping[str, Any]) -> str:
    if payload.get("output_text"):
        return str(payload["output_text"])
    parts: list[str] = []
    for output in payload.get("output", []):
        if not isinstance(output, Mapping):
            continue
        for content in output.get("content", []):
            if isinstance(content, Mapping) and content.get("text"):
                parts.append(str(content["text"]))
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError("OpenAI response did not include text content")
    return text


def _extract_gemini_text(payload: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for candidate in payload.get("candidates", []):
        if not isinstance(candidate, Mapping):
            continue
        content = candidate.get("content", {})
        if not isinstance(content, Mapping):
            continue
        for part in content.get("parts", []):
            if isinstance(part, Mapping) and part.get("text"):
                parts.append(str(part["text"]))
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError("Gemini response did not include text content")
    return text


def _normalize_provider(provider: str | None) -> str:
    value = str(provider or "anthropic").strip().lower()
    aliases = {
        "claude": "anthropic",
        "anthropic": "anthropic",
        "openai": "openai",
        "chatgpt": "openai",
        "gpt": "openai",
        "gemini": "gemini",
        "google": "gemini",
    }
    return aliases.get(value, value)


def build_fallback_agent_plan_response(parsed_playbook: Mapping[str, Any]) -> dict[str, Any]:
    desired = build_fallback_desired_config(parsed_playbook)
    ivr_requirements = parsed_playbook.get("ivr_requirements", {})
    return validate_agent_plan_response(
        {
            "client_name": desired["client_name"],
            "planned_calls": build_core_write_plan(
                {
                    "skills": desired["skills"],
                    "dispositions": desired["dispositions"],
                    "prompts": desired["prompts"],
                    "inbound_campaigns": desired["inbound_campaigns"],
                    "dnis": desired["dnis"],
                },
                default_ivr_script_name=ivr_requirements.get("script_name"),
            ),
            "ivr_requirements": ivr_requirements,
            "ivr_script_plan": _fallback_ivr_script_plan(ivr_requirements),
            "deferred_items": desired["deferred_items"],
            "rationale": desired["rationale"],
        }
    )


def _fallback_ivr_script_plan(ivr_requirements: Mapping[str, Any]) -> list[dict[str, Any]]:
    script_name = str(ivr_requirements.get("script_name") or "").strip()
    if not script_name:
        return []
    return [
        {
            "tool_name": "five9_create_ivr_script",
            "params": {"name": script_name},
        }
    ]


def _missing_key_fallback(env_name: str, fallback: dict[str, Any]) -> dict[str, Any]:
    return {
        "ai_mode": "fallback",
        "model": None,
        "agent_plan": fallback,
        "planned_calls": fallback["planned_calls"],
        "review_items": [
            {
                "severity": "info",
                "message": f"{env_name} is not set and no request API key was provided; deterministic fallback was used.",
            }
        ],
    }


def _provider_failure_fallback(
    provider_name: str,
    selected_model: str,
    fallback: dict[str, Any],
    exc: Exception,
) -> dict[str, Any]:
    return {
        "ai_mode": "fallback",
        "model": selected_model,
        "agent_plan": fallback,
        "planned_calls": fallback["planned_calls"],
        "review_items": [
            {
                "severity": "warning",
                "message": (
                    f"{provider_name} interpretation failed; deterministic fallback was used: "
                    f"{_sanitize_exception(exc)}"
                ),
            }
        ],
    }


def _sanitize_exception(exc: Exception) -> str:
    text = str(exc)
    replacements = [
        (r"([?&]key=)[^&\s]+", r"\1[redacted]"),
        (r"([?&]api_key=)[^&\s]+", r"\1[redacted]"),
        (r"(Bearer\s+)[A-Za-z0-9._\-]+", r"\1[redacted]"),
        (r"(x-api-key['\"]?\s*[:=]\s*['\"]?)[A-Za-z0-9._\-]+", r"\1[redacted]"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


__all__ = [
    "DEFAULT_ANTHROPIC_MODEL",
    "DEFAULT_GEMINI_MODEL",
    "DEFAULT_OPENAI_MODEL",
    "ALLOWED_CORE_WRITE_TOOL_NAMES",
    "build_fallback_agent_plan_response",
    "interpret_playbook_with_claude",
    "interpret_playbook_with_llm",
]
