from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SUPPORTED_PLATFORM = "five9"
DEFERRED_IVR_MESSAGE = (
    "IVR XML generation deferred; playbook intake may create the IVR script shell "
    "but does not generate or upload raw script XML."
)


def desired_config_contract_text() -> str:
    return (
        "Required Output JSON\n"
        "Return exactly one JSON object with these keys only: platform, client_name, "
        "skills, dispositions, prompts, inbound_campaigns, dnis, deferred_items, rationale.\n"
        "Do not return markdown. Do not wrap JSON in prose. Do not include extra keys.\n"
        "Do not execute tools. Do not include IVR script XML or IVR write requests. "
        "Do not include ivr_scripts.\n"
        "Field contract:\n"
        "- platform: string, must be \"five9\".\n"
        "- client_name: non-empty string.\n"
        "- skills: array of non-empty strings only. Never objects.\n"
        "- dispositions: array of non-empty strings only. Never objects.\n"
        "- prompts: array of objects with string prompt_name and string text.\n"
        "- inbound_campaigns: array of objects with string campaign_name, optional string "
        "description, skills string[], and dispositions string[].\n"
        "- dnis: array of objects with string number, optional string campaign_name, and optional string route_to.\n"
        "- deferred_items: array of strings.\n"
        "- rationale: string explaining normalization choices.\n"
        "Valid example:\n"
        "{"
        "\"platform\": \"five9\", "
        "\"client_name\": \"Jacuzzi\", "
        "\"skills\": [\"Main Agent - Tier 1\"], "
        "\"dispositions\": [\"Appointment Set\"], "
        "\"prompts\": [{\"prompt_name\": \"Main Greeting\", \"text\": \"Thank you for calling Jacuzzi.\"}], "
        "\"inbound_campaigns\": [{\"campaign_name\": \"JBRx Sales Main Agent Inbound\", "
        "\"description\": \"Main inbound line\", \"skills\": [\"Main Agent - Tier 1\"], "
        "\"dispositions\": [\"Appointment Set\"]}], "
        "\"dnis\": [{\"number\": \"8008852569\", \"campaign_name\": \"JBRx Sales Main Agent Inbound\"}], "
        "\"deferred_items\": [\"IVR script generation deferred\"], "
        "\"rationale\": \"Parsed from implementation playbook.\""
        "}\n"
        "Forbidden shapes, these will be rejected:\n"
        "- \"skills\": [{\"name\": \"Main Agent - Tier 1\"}]\n"
        "- \"skills\": [\"{'name': 'Main Agent - Tier 1'}\"]\n"
        "- \"dispositions\": [{\"name\": \"Appointment Set\"}]\n"
        "- \"dispositions\": [\"{'name': 'Appointment Set'}\"]\n"
        "- \"ivr_scripts\": [{\"name\": \"Main IVR\"}]\n"
        "If a skill or disposition has descriptive metadata, summarize it in rationale; "
        "do not place descriptions inside skills or dispositions."
    )


CORE_WRITE_PARAM_SCHEMAS: dict[str, dict[str, Any]] = {
    "five9_create_skill": {
        "required": {"name": "string"},
        "optional": {
            "description": "string",
            "route_voice_mails": "boolean",
            "message_of_the_day": "string",
        },
    },
    "five9_create_disposition": {
        "required": {"name": "string"},
        "optional": {
            "description": "string",
            "agent_must_complete_worksheet": "boolean",
            "agent_must_confirm": "boolean",
            "reset_attempts_counter": "boolean",
        },
    },
    "five9_add_prompt_tts": {
        "required": {"prompt_name": "string", "text": "string"},
        "optional": {"description": "string", "voice": "string", "language": "string"},
    },
    "five9_create_inbound_campaign": {
        "required": {"campaign_name": "string"},
        "optional": {"description": "string", "max_num_of_lines": "integer"},
    },
    "five9_add_dnis_to_campaign": {
        "required": {"campaign_name": "string", "dnis": "string_list"},
        "optional": {},
    },
    "five9_add_skills_to_campaign": {
        "required": {"campaign_name": "string", "skills": "string_list"},
        "optional": {},
    },
    "five9_add_dispositions_to_campaign": {
        "required": {"campaign_name": "string", "dispositions": "string_list"},
        "optional": {"is_skip_preview_disposition": "boolean"},
    },
    "five9_set_default_ivr_schedule": {
        "required": {"campaign_name": "string", "script_name": "string"},
        "optional": {"params": "object", "is_visual_mode_enabled": "boolean"},
    },
}

ALLOWED_CORE_WRITE_TOOL_NAMES = list(CORE_WRITE_PARAM_SCHEMAS.keys())
IVR_SCRIPT_CREATE_PARAM_SCHEMAS: dict[str, dict[str, Any]] = {
    "five9_create_ivr_script": {
        "required": {"name": "string"},
        "optional": {},
    }
}
ALLOWED_PLAYBOOK_IVR_SCRIPT_TOOL_NAMES = list(IVR_SCRIPT_CREATE_PARAM_SCHEMAS.keys())


def planned_calls_contract_text() -> str:
    return (
        "Required Output JSON\n"
        "Return exactly one JSON object with these keys only: client_name, planned_calls, "
        "ivr_requirements, ivr_script_plan, deferred_items, rationale.\n"
        "Do not return markdown. Do not wrap JSON in prose. Do not include extra keys. "
        "Do not output raw SOAP XML. No IVR XML. Do not execute tools.\n"
        "planned_calls must be an array of objects with exactly tool_name and params.\n"
        "ivr_requirements is planning-only data with script_name, intent, business_hours, "
        "greetings string[], menu_options objects, routing_targets string[], and notes string[].\n"
        "menu_options objects must contain digit, label, and target strings.\n"
        "ivr_script_plan may contain only five9_create_ivr_script with params.name. "
        "This creates the IVR script shell only; it must not include XML.\n"
        "Allowed tool contracts:\n"
        "- five9_create_skill params: name string required; optional description string, "
        "route_voice_mails boolean, message_of_the_day string.\n"
        "- five9_create_disposition params: name string required; optional description string, "
        "agent_must_complete_worksheet boolean, agent_must_confirm boolean, reset_attempts_counter boolean.\n"
        "- five9_add_prompt_tts params: prompt_name string required, text string required; "
        "optional description string, voice string, language string.\n"
        "- five9_create_inbound_campaign params: campaign_name string required; "
        "optional description string, max_num_of_lines integer.\n"
        "- five9_add_dnis_to_campaign params: campaign_name string required, dnis string[] required.\n"
        "- five9_add_skills_to_campaign params: campaign_name string required, skills string[] required.\n"
        "- five9_add_dispositions_to_campaign params: campaign_name string required, "
        "dispositions string[] required; optional is_skip_preview_disposition boolean.\n"
        "- five9_set_default_ivr_schedule params: campaign_name string required, script_name string required; "
        "optional params object, is_visual_mode_enabled boolean.\n"
        "Valid example:\n"
        "{"
        "\"client_name\": \"Jacuzzi\", "
        "\"planned_calls\": ["
        "{\"tool_name\": \"five9_create_skill\", "
        "\"params\": {\"name\": \"Main Agent - Tier 1\", "
        "\"description\": \"Primary sales agent skill from Jacuzzi playbook\"}}, "
        "{\"tool_name\": \"five9_create_disposition\", "
        "\"params\": {\"name\": \"Appointment Set\"}}, "
        "{\"tool_name\": \"five9_create_inbound_campaign\", "
        "\"params\": {\"campaign_name\": \"JBRx Sales Main Agent Inbound\", "
        "\"description\": \"Main inbound line\"}}, "
        "{\"tool_name\": \"five9_add_skills_to_campaign\", "
        "\"params\": {\"campaign_name\": \"JBRx Sales Main Agent Inbound\", "
        "\"skills\": [\"Main Agent - Tier 1\"]}}"
        "], "
        "\"ivr_requirements\": {\"script_name\": \"Main IVR\", "
        "\"intent\": \"Route inbound callers by menu option\", "
        "\"business_hours\": \"\", "
        "\"greetings\": [\"Main Greeting\"], "
        "\"menu_options\": [{\"digit\": \"1\", \"label\": \"Sales\", \"target\": \"Main Agent - Tier 1\"}], "
        "\"routing_targets\": [\"Main Agent - Tier 1\"], "
        "\"notes\": [\"IVR XML generation deferred\"]}, "
        "\"ivr_script_plan\": [{\"tool_name\": \"five9_create_ivr_script\", "
        "\"params\": {\"name\": \"Main IVR\"}}], "
        "\"deferred_items\": [\"IVR scripts deferred\"], "
        "\"rationale\": \"Built from Jacuzzi implementation playbook.\""
        "}\n"
        "Forbidden shapes, these will be rejected:\n"
        "- {\"tool_name\": \"five9_delete_skill\", \"params\": {\"name\": \"Skill\"}}\n"
        "- {\"tool_name\": \"five9_modify_ivr_script\", \"params\": {\"name\": \"Main IVR\"}}\n"
        "- {\"tool_name\": \"five9_delete_ivr_script\", \"params\": {\"name\": \"Main IVR\"}}\n"
        "- \"xmlDefinition\" or \"xml_definition\" anywhere in the response\n"
        "- {\"tool_name\": \"five9_create_skill\", \"params\": {\"name\": {\"name\": \"Skill\"}}}\n"
        "- {\"tool_name\": \"five9_add_skills_to_campaign\", \"params\": {\"skills\": [{\"name\": \"Skill\"}]}}\n"
        "- Any params not listed in the allowed tool contracts."
    )


def validate_agent_plan_response(value: Mapping[str, Any]) -> dict[str, Any]:
    response = deepcopy(dict(value))
    _reject_forbidden_ivr_xml(response, "agent_plan")
    allowed_top_level = {
        "client_name",
        "planned_calls",
        "ivr_requirements",
        "ivr_script_plan",
        "deferred_items",
        "rationale",
    }
    extra_keys = set(response) - allowed_top_level
    if extra_keys:
        raise ValueError(f"Agent plan response includes unsupported keys: {sorted(extra_keys)}")
    client_name = _clean_identity_text(response.get("client_name"), "client_name")
    planned_calls = validate_planned_calls(response.get("planned_calls", []))
    ivr_requirements = validate_ivr_requirements(response.get("ivr_requirements", {}))
    ivr_script_plan = validate_ivr_script_plan(response.get("ivr_script_plan", []))
    deferred_items = _string_list(response.get("deferred_items", []), "deferred_items")
    rationale = response.get("rationale") or ""
    if not isinstance(rationale, str):
        raise ValueError("rationale must be a string")
    return {
        "client_name": client_name,
        "planned_calls": planned_calls,
        "ivr_requirements": ivr_requirements,
        "ivr_script_plan": ivr_script_plan,
        "deferred_items": deferred_items,
        "rationale": rationale.strip(),
    }


def validate_ivr_requirements(value: Any) -> dict[str, Any]:
    if value in (None, ""):
        value = {}
    if not isinstance(value, Mapping):
        raise ValueError("ivr_requirements must be an object")
    _reject_forbidden_ivr_xml(value, "ivr_requirements")
    allowed_keys = {
        "script_name",
        "intent",
        "business_hours",
        "greetings",
        "menu_options",
        "routing_targets",
        "notes",
    }
    extra_keys = set(value) - allowed_keys
    if extra_keys:
        raise ValueError(f"ivr_requirements has unsupported keys: {sorted(extra_keys)}")
    return {
        "script_name": _optional_planning_text(value.get("script_name"), "ivr_requirements.script_name"),
        "intent": _optional_planning_text(value.get("intent"), "ivr_requirements.intent"),
        "business_hours": _optional_planning_text(value.get("business_hours"), "ivr_requirements.business_hours"),
        "greetings": _planning_string_list(value.get("greetings", []), "ivr_requirements.greetings"),
        "menu_options": _ivr_menu_options(value.get("menu_options", [])),
        "routing_targets": _planning_string_list(value.get("routing_targets", []), "ivr_requirements.routing_targets"),
        "notes": _planning_string_list(value.get("notes", []), "ivr_requirements.notes"),
    }


def validate_ivr_script_plan(values: Any) -> list[dict[str, Any]]:
    return _validate_plans_for_schemas(
        values,
        IVR_SCRIPT_CREATE_PARAM_SCHEMAS,
        "ivr_script_plan",
    )


def validate_agent_executable_plan(values: Any) -> list[dict[str, Any]]:
    schemas = {**CORE_WRITE_PARAM_SCHEMAS, **IVR_SCRIPT_CREATE_PARAM_SCHEMAS}
    return _validate_plans_for_schemas(values, schemas, "planned_calls")


def validate_planned_calls(values: Any) -> list[dict[str, Any]]:
    return _validate_plans_for_schemas(values, CORE_WRITE_PARAM_SCHEMAS, "planned_calls")


def _validate_plans_for_schemas(
    values: Any,
    schemas: Mapping[str, dict[str, Any]],
    field_name: str,
) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        raise ValueError(f"{field_name} must be a list")
    validated: list[dict[str, Any]] = []
    for index, call in enumerate(values):
        if not isinstance(call, Mapping):
            raise ValueError(f"{field_name}[{index}] must be an object")
        allowed_call_keys = {"tool_name", "params"}
        extra_call_keys = set(call) - allowed_call_keys
        if extra_call_keys:
            raise ValueError(f"{field_name}[{index}] has unsupported keys: {sorted(extra_call_keys)}")
        tool_name = _clean_identity_text(call.get("tool_name"), f"{field_name}[{index}].tool_name")
        if tool_name not in schemas:
            raise ValueError(f"{field_name}[{index}].tool_name is not an allowed tool: {tool_name}")
        params = call.get("params")
        if not isinstance(params, Mapping):
            raise ValueError(f"{field_name}[{index}].params must be an object")
        validated.append(
            {
                "tool_name": tool_name,
                "params": _validate_tool_params(
                    tool_name,
                    params,
                    f"{field_name}[{index}].params",
                    schemas,
                ),
            }
        )
    return validated


def planned_calls_to_playbook_entities(planned_calls: list[dict[str, Any]]) -> dict[str, Any]:
    validated_calls = validate_planned_calls(planned_calls)
    campaigns_by_name: dict[str, dict[str, Any]] = {}
    skills: list[str] = []
    dispositions: list[str] = []
    prompts: list[dict[str, str]] = []
    dnis: list[dict[str, str]] = []

    for call in validated_calls:
        tool_name = call["tool_name"]
        params = call["params"]
        if tool_name == "five9_create_skill":
            _append_unique(skills, params["name"])
        elif tool_name == "five9_create_disposition":
            _append_unique(dispositions, params["name"])
        elif tool_name == "five9_add_prompt_tts":
            prompts.append({"prompt_name": params["prompt_name"], "text": params["text"]})
        elif tool_name == "five9_create_inbound_campaign":
            campaign = campaigns_by_name.setdefault(
                params["campaign_name"],
                {
                    "campaign_name": params["campaign_name"],
                    "description": params.get("description"),
                    "skills": [],
                    "dispositions": [],
                },
            )
            if params.get("description"):
                campaign["description"] = params["description"]
        elif tool_name == "five9_add_skills_to_campaign":
            campaign = campaigns_by_name.setdefault(
                params["campaign_name"],
                {
                    "campaign_name": params["campaign_name"],
                    "description": None,
                    "skills": [],
                    "dispositions": [],
                },
            )
            for skill in params["skills"]:
                _append_unique(campaign["skills"], skill)
        elif tool_name == "five9_add_dispositions_to_campaign":
            campaign = campaigns_by_name.setdefault(
                params["campaign_name"],
                {
                    "campaign_name": params["campaign_name"],
                    "description": None,
                    "skills": [],
                    "dispositions": [],
                },
            )
            for disposition in params["dispositions"]:
                _append_unique(campaign["dispositions"], disposition)
        elif tool_name == "five9_add_dnis_to_campaign":
            for number in params["dnis"]:
                dnis.append({"number": number, "campaign_name": params["campaign_name"]})

    return {
        "skills": skills,
        "dispositions": dispositions,
        "prompts": prompts,
        "inbound_campaigns": list(campaigns_by_name.values()),
        "dnis": dnis,
    }


def _ivr_menu_options(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        raise ValueError("ivr_requirements.menu_options must be a list")
    options: list[dict[str, str]] = []
    for index, item in enumerate(values):
        if not isinstance(item, Mapping):
            raise ValueError(f"ivr_requirements.menu_options[{index}] must be an object")
        allowed_keys = {"digit", "label", "target"}
        extra_keys = set(item) - allowed_keys
        if extra_keys:
            raise ValueError(
                f"ivr_requirements.menu_options[{index}] has unsupported keys: {sorted(extra_keys)}"
            )
        options.append(
            {
                "digit": _clean_identity_text(
                    item.get("digit"),
                    f"ivr_requirements.menu_options[{index}].digit",
                ),
                "label": _clean_identity_text(
                    item.get("label"),
                    f"ivr_requirements.menu_options[{index}].label",
                ),
                "target": _clean_identity_text(
                    item.get("target"),
                    f"ivr_requirements.menu_options[{index}].target",
                ),
            }
        )
    return options


def _validate_tool_params(
    tool_name: str,
    params: Mapping[str, Any],
    path: str,
    schemas: Mapping[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    schema = (schemas or CORE_WRITE_PARAM_SCHEMAS)[tool_name]
    allowed_params = set(schema["required"]) | set(schema["optional"])
    extra_params = set(params) - allowed_params
    if extra_params:
        raise ValueError(f"{path} has unsupported params: {sorted(extra_params)}")
    output: dict[str, Any] = {}
    for name, expected_type in schema["required"].items():
        if name not in params:
            raise ValueError(f"{path}.{name} is required")
        output[name] = _validate_param_value(params[name], expected_type, f"{path}.{name}")
    for name, expected_type in schema["optional"].items():
        if name in params:
            output[name] = _validate_param_value(params[name], expected_type, f"{path}.{name}")
    return output


def _validate_param_value(value: Any, expected_type: str, path: str) -> Any:
    if expected_type == "string":
        return _clean_identity_text(value, path)
    if expected_type == "string_list":
        return _string_list(value, path)
    if expected_type == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"{path} must be a boolean")
        return value
    if expected_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{path} must be an integer")
        return value
    if expected_type == "object":
        if not isinstance(value, Mapping):
            raise ValueError(f"{path} must be an object")
        return deepcopy(dict(value))
    raise ValueError(f"Unsupported expected type for {path}: {expected_type}")


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _optional_planning_text(value: Any, field_path: str) -> str:
    if value in (None, ""):
        return ""
    return _clean_identity_text(value, field_path)


def _planning_string_list(values: Any, field_name: str) -> list[str]:
    if not isinstance(values, list):
        raise ValueError(f"{field_name} must be a list")
    output: list[str] = []
    seen = set()
    for index, value in enumerate(values):
        text = _clean_identity_text(value, f"{field_name}[{index}]")
        if text not in seen:
            seen.add(text)
            output.append(text)
    return output


def _reject_forbidden_ivr_xml(value: Any, path: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            key_lower = key_text.lower()
            child_path = f"{path}.{key_text}"
            if key_lower in {"xmldefinition", "xml_definition"}:
                raise ValueError(f"{child_path} is not allowed in Playbook Agent IVR planning output")
            _reject_forbidden_ivr_xml(child, child_path)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_ivr_xml(child, f"{path}[{index}]")
        return
    if isinstance(value, str):
        lowered = value.lower()
        if "<ivrscript" in lowered or "<ivr-script" in lowered or "xmldefinition" in lowered or "xml_definition" in lowered:
            raise ValueError(f"{path} contains IVR XML content, which is not allowed")


def validate_desired_config(value: Mapping[str, Any]) -> dict[str, Any]:
    desired = deepcopy(dict(value))
    platform = str(desired.get("platform") or "").strip().lower()
    client_name = str(desired.get("client_name") or "").strip()

    if platform != SUPPORTED_PLATFORM:
        raise ValueError("Only Five9 desired configuration is supported in this agent slice")
    if not client_name:
        raise ValueError("client_name is required")
    if desired.get("ivr_scripts"):
        raise ValueError("IVR script generation is deferred and cannot be requested here")

    normalized = {
        "platform": SUPPORTED_PLATFORM,
        "client_name": client_name,
        "skills": _string_list(desired.get("skills", []), "skills"),
        "dispositions": _string_list(desired.get("dispositions", []), "dispositions"),
        "prompts": _prompt_list(desired.get("prompts", [])),
        "inbound_campaigns": _campaign_list(desired.get("inbound_campaigns", [])),
        "dnis": _dnis_list(desired.get("dnis", [])),
        "deferred_items": _string_list(desired.get("deferred_items", []), "deferred_items"),
        "rationale": str(desired.get("rationale") or "").strip(),
    }
    if DEFERRED_IVR_MESSAGE not in normalized["deferred_items"]:
        normalized["deferred_items"].append(DEFERRED_IVR_MESSAGE)
    return normalized


def build_fallback_desired_config(parsed: Mapping[str, Any]) -> dict[str, Any]:
    entities = parsed.get("entities", {})
    client_name = _client_name_from_source(parsed)
    return validate_desired_config(
        {
            "platform": SUPPORTED_PLATFORM,
            "client_name": client_name,
            "skills": entities.get("skills", []),
            "dispositions": entities.get("dispositions", []),
            "prompts": entities.get("prompts", []),
            "inbound_campaigns": entities.get("inbound_campaigns", []),
            "dnis": entities.get("dnis", []),
            "deferred_items": parsed.get("deferred", [DEFERRED_IVR_MESSAGE]),
            "rationale": "Deterministic fallback generated from workbook tabs.",
        }
    )


def desired_to_compare_input(desired: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "skills": list(desired.get("skills", [])),
        "dispositions": list(desired.get("dispositions", [])),
        "prompts": [
            {"name": prompt["prompt_name"]}
            for prompt in desired.get("prompts", [])
            if prompt.get("prompt_name")
        ],
        "campaigns": [
            {"name": campaign["campaign_name"]}
            for campaign in desired.get("inbound_campaigns", [])
            if campaign.get("campaign_name")
        ],
        "dnis": list(desired.get("dnis", [])),
    }


def desired_to_playbook_entities(desired: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "skills": list(desired.get("skills", [])),
        "dispositions": list(desired.get("dispositions", [])),
        "prompts": deepcopy(list(desired.get("prompts", []))),
        "inbound_campaigns": deepcopy(list(desired.get("inbound_campaigns", []))),
        "dnis": deepcopy(list(desired.get("dnis", []))),
    }


def _string_list(values: Any, field_name: str) -> list[str]:
    if not isinstance(values, list):
        raise ValueError(f"{field_name} must be a list")
    output: list[str] = []
    seen = set()
    for index, value in enumerate(values):
        text = _clean_identity_text(value, f"{field_name}[{index}]")
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return output


def _prompt_list(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        raise ValueError("prompts must be a list")
    prompts: list[dict[str, str]] = []
    seen = set()
    for index, item in enumerate(values):
        if not isinstance(item, Mapping):
            raise ValueError(f"prompts[{index}] must be an object")
        name = _clean_identity_text(
            item.get("prompt_name") or item.get("name"),
            f"prompts[{index}].prompt_name",
        )
        raw_text = item.get("text") or ""
        if not isinstance(raw_text, str):
            raise ValueError(f"prompts[{index}].text must be a string")
        text = raw_text.strip()
        if name and name not in seen:
            seen.add(name)
            prompts.append({"prompt_name": name, "text": text})
    return prompts


def _campaign_list(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        raise ValueError("inbound_campaigns must be a list")
    campaigns: list[dict[str, Any]] = []
    seen = set()
    for index, item in enumerate(values):
        if not isinstance(item, Mapping):
            raise ValueError(f"inbound_campaigns[{index}] must be an object")
        name = _clean_identity_text(
            item.get("campaign_name") or item.get("name"),
            f"inbound_campaigns[{index}].campaign_name",
        )
        if not name or name in seen:
            continue
        description = item.get("description") or ""
        if not isinstance(description, str):
            raise ValueError(f"inbound_campaigns[{index}].description must be a string")
        seen.add(name)
        campaigns.append(
            {
                "campaign_name": name,
                "description": description.strip() or None,
                "skills": _string_list(item.get("skills", []), f"inbound_campaigns[{index}].skills"),
                "dispositions": _string_list(
                    item.get("dispositions", []),
                    f"inbound_campaigns[{index}].dispositions",
                ),
            }
        )
    return campaigns


def _dnis_list(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        raise ValueError("dnis must be a list")
    dnis: list[dict[str, str]] = []
    seen = set()
    for index, item in enumerate(values):
        if not isinstance(item, Mapping):
            raise ValueError(f"dnis[{index}] must be an object")
        number = _clean_identity_text(
            item.get("number") or item.get("dnis"),
            f"dnis[{index}].number",
        )
        campaign_name = _optional_identity_text(
            item.get("campaign_name") or item.get("campaign"),
            f"dnis[{index}].campaign_name",
        )
        route_to = _optional_identity_text(item.get("route_to"), f"dnis[{index}].route_to")
        if not number:
            continue
        identity = (number, campaign_name, route_to)
        if identity in seen:
            continue
        seen.add(identity)
        entry = {"number": number}
        if campaign_name:
            entry["campaign_name"] = campaign_name
        if route_to:
            entry["route_to"] = route_to
        dnis.append(entry)
    return dnis


def _optional_identity_text(value: Any, field_path: str) -> str:
    if value in (None, ""):
        return ""
    return _clean_identity_text(value, field_path)


def _clean_identity_text(value: Any, field_path: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_path} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field_path} must not be blank")
    if _looks_like_serialized_object(text):
        raise ValueError(f"{field_path} looks like serialized object data")
    return text


def _looks_like_serialized_object(text: str) -> bool:
    stripped = text.strip()
    if (stripped.startswith("{") and stripped.endswith("}")) or (
        stripped.startswith("[") and stripped.endswith("]")
    ):
        return True
    lowered = stripped.lower()
    suspicious_tokens = (
        "'name'",
        '"name"',
        "'number'",
        '"number"',
        "'campaign_name'",
        '"campaign_name"',
        "'prompt_name'",
        '"prompt_name"',
    )
    return any(token in lowered for token in suspicious_tokens)


def _client_name_from_source(parsed: Mapping[str, Any]) -> str:
    source = parsed.get("source", {})
    file_name = str(source.get("file_name") or "Imported Playbook")
    stem = file_name.rsplit(".", 1)[0]
    for marker in ("Implementation Playbook Template -", "Implementation Playbook -"):
        if marker in stem:
            return stem.split(marker, 1)[1].strip() or "Imported Playbook"
    return stem.strip() or "Imported Playbook"


__all__ = [
    "DEFERRED_IVR_MESSAGE",
    "ALLOWED_CORE_WRITE_TOOL_NAMES",
    "ALLOWED_PLAYBOOK_IVR_SCRIPT_TOOL_NAMES",
    "CORE_WRITE_PARAM_SCHEMAS",
    "IVR_SCRIPT_CREATE_PARAM_SCHEMAS",
    "build_fallback_desired_config",
    "desired_config_contract_text",
    "desired_to_compare_input",
    "desired_to_playbook_entities",
    "planned_calls_contract_text",
    "planned_calls_to_playbook_entities",
    "validate_agent_plan_response",
    "validate_agent_executable_plan",
    "validate_ivr_requirements",
    "validate_ivr_script_plan",
    "validate_planned_calls",
    "validate_desired_config",
]
