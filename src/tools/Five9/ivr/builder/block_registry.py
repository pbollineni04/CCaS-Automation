from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping
from xml.etree import ElementTree as ET


CORPUS_BACKED_MODULE_CATALOG: dict[str, dict[str, Any]] = {
    "incomingCall": {
        "generation_status": "supported_v1",
        "required_fields": ["moduleName", "moduleId", "singleDescendant"],
        "output_behavior": "Entry point for the IVR graph.",
        "example": "START_Acme_Main_IVR -> Greeting",
    },
    "play": {
        "generation_status": "supported_v1",
        "required_fields": ["moduleName", "moduleId", "singleDescendant", "prompt"],
        "output_behavior": "Plays a corpus-shaped prompt block before menu routing.",
        "example": "Greeting -> Main Menu",
    },
    "menu": {
        "generation_status": "supported_v1",
        "required_fields": ["name", "digit", "label", "target"],
        "optional_fields": ["no_match", "no_input"],
        "output_behavior": "Branches DTMF choices to transfer modules using Five9 branch entries.",
        "example": "1 -> Sales skillTransfer, 2 -> Billing skillTransfer",
    },
    "skillTransfer": {
        "generation_status": "supported_v1",
        "required_fields": ["target"],
        "output_behavior": "Transfers the caller to a named Five9 skill with queue defaults.",
        "example": "target=Sales",
    },
    "campaignTransfer": {
        "generation_status": "unsupported_no_corpus_evidence",
        "required_fields": ["target"],
        "output_behavior": "Not generated until a real exported campaignTransfer shape is captured.",
        "example": "blocked in v1",
    },
    "hangup": {
        "generation_status": "supported_v1",
        "required_fields": ["moduleName", "moduleId"],
        "output_behavior": "Terminates the call flow with disposition/error defaults.",
        "example": "No Match -> Hangup",
    },
    "startOnHangup": {
        "generation_status": "supported_v1",
        "required_fields": ["moduleName", "moduleId", "singleDescendant"],
        "output_behavior": "Entry point for the mandatory modulesOnHangup mini-flow.",
    },
    "setVariable": {
        "generation_status": "documented_only",
        "required_fields": ["variableName", "value"],
        "output_behavior": "Sets IVR runtime variables; parsed but not generated in v1.",
    },
    "getDigits": {
        "generation_status": "documented_only",
        "required_fields": ["targetVariableName", "numberOfDigits"],
        "output_behavior": "Collects DTMF digits; parsed but not generated in v1.",
    },
    "case": {
        "generation_status": "documented_only",
        "required_fields": ["branches"],
        "output_behavior": "Branches by value comparisons; parsed but not generated in v1.",
    },
    "ifElse": {
        "generation_status": "documented_only",
        "required_fields": ["conditions", "branches"],
        "output_behavior": "Branches by condition; parsed but not generated in v1.",
    },
    "query": {
        "generation_status": "documented_only",
        "required_fields": ["url", "method"],
        "output_behavior": "Calls an external HTTP endpoint; parsed but not generated in v1.",
    },
    "foreignScript": {
        "generation_status": "documented_only",
        "required_fields": ["ivrScript", "params", "returnVals"],
        "output_behavior": "Calls another IVR script; parsed but not generated in v1.",
    },
    "voiceMailTransfer": {
        "generation_status": "documented_only",
        "required_fields": ["vmBoxType", "vmPersonalBox", "vmSkillBox"],
        "output_behavior": "Transfers caller to voicemail; parsed but not generated in v1.",
    },
    "thirdPartyTransfer": {
        "generation_status": "documented_only",
        "required_fields": ["thirdPartyNumber"],
        "output_behavior": "Transfers to an external destination; parsed but not generated in v1.",
    },
    "agentTransfer": {
        "generation_status": "documented_only",
        "required_fields": ["agentToTransfer"],
        "output_behavior": "Transfers caller to a specific agent; parsed but not generated in v1.",
    },
    "input": {
        "generation_status": "documented_only",
        "required_fields": ["grammar", "recoEvents"],
        "output_behavior": "Collects voice or DTMF input; parsed but not generated in v1.",
    },
    "extensionTransfer": {
        "generation_status": "documented_only",
        "required_fields": ["maxTime", "maxSilence"],
        "output_behavior": "Transfers caller to an extension; parsed but not generated in v1.",
    },
    "ivaTransfer": {
        "generation_status": "documented_only",
        "required_fields": ["sendData", "receiveData"],
        "output_behavior": "Transfers caller to IVA/NLP handling; parsed but not generated in v1.",
    },
    "answerMachine": {
        "generation_status": "documented_only",
        "required_fields": ["branches", "maxToneTime", "waitTone"],
        "output_behavior": "Branches based on answering machine detection; parsed but not generated in v1.",
    },
    "language": {
        "generation_status": "documented_only",
        "required_fields": ["items", "selectionMode"],
        "output_behavior": "Sets or selects IVR language; parsed but not generated in v1.",
    },
    "lookupCRMRecord": {
        "generation_status": "documented_only",
        "required_fields": ["conditions", "lookupCriteria"],
        "output_behavior": "Looks up a CRM record; parsed but not generated in v1.",
    },
    "crmUpdate": {
        "generation_status": "documented_only",
        "required_fields": ["selectedFields", "mode"],
        "output_behavior": "Updates a CRM record; parsed but not generated in v1.",
    },
    "systemInfo": {
        "generation_status": "documented_only",
        "required_fields": ["systemInfoType", "targetResultVariableNames"],
        "output_behavior": "Reads Five9/system runtime data; parsed but not generated in v1.",
    },
    "systemUpdate": {
        "generation_status": "documented_only",
        "required_fields": ["objectToModify", "fieldsToModify"],
        "output_behavior": "Updates Five9/system runtime data; parsed but not generated in v1.",
    },
    "iterator": {
        "generation_status": "documented_only",
        "required_fields": ["mode", "operation"],
        "output_behavior": "Iterates over a collection; parsed but not generated in v1.",
    },
    "setDNC": {
        "generation_status": "documented_only",
        "required_fields": ["targetVariableName"],
        "output_behavior": "Sets Do Not Call state; parsed but not generated in v1.",
    },
    "conference": {
        "generation_status": "documented_only",
        "required_fields": ["recognitionEvents", "maxNumberOfParticipants"],
        "output_behavior": "Starts a conference call leg; parsed but not generated in v1.",
    },
    "recording": {
        "generation_status": "documented_only",
        "required_fields": ["recoEvents", "maxTime", "varToAccessRecording"],
        "output_behavior": "Controls call recording; parsed but not generated in v1.",
    },
}

OBSERVED_MODULE_TYPES: tuple[str, ...] = (
    "incomingCall",
    "startOnHangup",
    "hangup",
    "play",
    "menu",
    "getDigits",
    "input",
    "language",
    "recording",
    "setVariable",
    "ifElse",
    "case",
    "iterator",
    "skillTransfer",
    "voiceMailTransfer",
    "thirdPartyTransfer",
    "agentTransfer",
    "extensionTransfer",
    "ivaTransfer",
    "query",
    "foreignScript",
    "lookupCRMRecord",
    "crmUpdate",
    "systemInfo",
    "systemUpdate",
    "setDNC",
    "answerMachine",
    "conference",
)

SUPPORTED_V1_MODULE_TYPES: tuple[str, ...] = (
    "incomingCall",
    "startOnHangup",
    "hangup",
    "play",
    "menu",
    "skillTransfer",
)

LOCKED_MODULE_TYPES: tuple[str, ...] = ("campaignTransfer",)


for _module_type in OBSERVED_MODULE_TYPES:
    entry = CORPUS_BACKED_MODULE_CATALOG.setdefault(
        _module_type,
        {
            "required_fields": [],
            "output_behavior": "Compiler candidate derived from observed Five9 IVR exports.",
        },
    )
    if _module_type in SUPPORTED_V1_MODULE_TYPES:
        entry["generation_status"] = "supported_v1"
        cert_status = "core_supported"
    else:
        entry["generation_status"] = "compiler_candidate"
        cert_status = "pending"
    entry.setdefault("required_fields", [])
    entry.setdefault("optional_fields", ["moduleName", "locationX", "locationY", "singleDescendant", "branches"])
    entry["certification"] = {
        "status": cert_status,
        "target_script": "ZZ_TEST_Codex_IVR_ModuleLab",
        "notes": (
            "Core V1 block" if cert_status == "core_supported"
            else "Generated from sanitized corpus-backed defaults; live modify/readback certification pending."
        ),
    }

for _module_type in LOCKED_MODULE_TYPES:
    entry = CORPUS_BACKED_MODULE_CATALOG.setdefault(_module_type, {})
    entry["generation_status"] = "unsupported_no_corpus_evidence"
    entry["certification"] = {
        "status": "blocked",
        "target_script": "ZZ_TEST_Codex_IVR_ModuleLab",
        "notes": "No real exported Five9 campaignTransfer module was found in the corpus.",
    }


def registry_copy() -> dict[str, dict[str, Any]]:
    return deepcopy(CORPUS_BACKED_MODULE_CATALOG)


def append_incoming_call(
    modules: ET.Element,
    script_name: str,
    module_id: str,
    next_id: str,
    safe_name: str,
    x: int = 40,
    y: int = 180,
) -> None:
    module = ET.SubElement(modules, "incomingCall")
    _text(module, "singleDescendant", next_id)
    _text(module, "moduleName", "START_" + safe_name)
    _text(module, "locationX", x)
    _text(module, "locationY", y)
    _text(module, "moduleId", module_id)
    ET.SubElement(module, "data")


def append_play(
    modules: ET.Element,
    greeting: Mapping[str, Any],
    module_id: str,
    ascendant: str,
    next_id: str,
    x: int = 220,
    y: int = 180,
) -> None:
    module = ET.SubElement(modules, "play")
    _text(module, "ascendants", ascendant)
    _text(module, "singleDescendant", next_id)
    _text(module, "moduleName", "Greeting")
    _text(module, "locationX", x)
    _text(module, "locationY", y)
    _text(module, "moduleId", module_id)

    data = ET.SubElement(module, "data")
    prompt = ET.SubElement(data, "prompt")
    _append_tts_prompt(prompt, str(greeting.get("text") or ""), str(greeting.get("prompt_name") or ""))
    _append_prompt_flags(prompt)
    _append_dispo(data, "0", "No Disposition")
    _append_empty_prompt_block(data, "vivrPrompts")
    _append_empty_prompt_block(data, "vivrHeader")
    _append_text_channel_data(data)
    _text(data, "numberOfDigits", "0")
    _text(data, "terminateDigit", "")
    _text(data, "clearDigitBuffer", "false")
    _text(data, "collapsible", "false")
    _append_email_prompt(data, "emailReplySubject")
    _append_email_prompt(data, "emailReplyBody")


def append_menu(
    modules: ET.Element,
    menu: Mapping[str, Any],
    module_id: str,
    ascendant: str,
    hangup_id: str,
    option_targets: list[dict[str, str]],
    x: int = 420,
    y: int = 180,
) -> None:
    module = ET.SubElement(modules, "menu")
    _text(module, "ascendants", ascendant)
    _text(module, "moduleName", str(menu.get("name") or "Main Menu"))
    _text(module, "locationX", x)
    _text(module, "locationY", y)
    _text(module, "moduleId", module_id)

    data = ET.SubElement(module, "data")
    _append_dispo(data, "0", "No Disposition")
    _append_empty_prompt_block(data, "vivrPrompts")
    _append_empty_prompt_block(data, "vivrHeader")
    _append_text_channel_data(data)

    branches = ET.SubElement(data, "branches")
    for option in option_targets:
        _append_branch(branches, option["digit"], option["label"], option["module_id"])
    _append_branch(branches, "No Match", "No Match", hangup_id)
    _append_branch(branches, "No Input", "No Input", hangup_id)

    _text(data, "useSpeechRecognition", "false")
    _text(data, "useDTMF", "true")
    _text(data, "recordUserInput", "false")
    _text(data, "maxAttempts", "3")
    _text(data, "confidenceTreshold", "50")
    ET.SubElement(data, "saveInput")
    ET.SubElement(data, "saveConfidenceLevel")
    _append_recognition_event(data, "NO_MATCH")
    _append_recognition_event(data, "NO_INPUT")
    _append_menu_prompt_count(data)
    _append_confirm_data(data)

    for option in option_targets:
        item = ET.SubElement(data, "items")
        choice = ET.SubElement(item, "choice")
        _text(choice, "type", "TEXT")
        _text(choice, "value", option["label"])
        _text(choice, "showInVivr", "true")
        _text(item, "match", option["label"])
        thumbnail = ET.SubElement(item, "thumbnail")
        _text(thumbnail, "type", "NONE")
        _text(thumbnail, "value", "")
        _text(thumbnail, "showInVivr", "false")
        _text(item, "dtmf", option["digit"])
        _text(item, "actionType", "MODULE")
        _text(item, "actionName", option["label"])

    _text(data, "maxTimeToEnter", "5")
    _text(data, "noInputTimeout", "5")
    _text(data, "speechCompleteTimeout", "1")
    _text(data, "collapsible", "false")
    _text(data, "sensitivity", "50")
    _text(data, "incompleteTimeout", "1")
    _text(data, "swirecNbestListLength", "1")
    _append_recognize_config_parameters(data)


def append_skill_transfer(
    modules: ET.Element,
    option: Mapping[str, str],
    ascendant: str,
    hangup_id: str,
    x: int | None = None,
    y: int | None = None,
) -> None:
    module = ET.SubElement(modules, "skillTransfer")
    _text(module, "ascendants", ascendant)
    _text(module, "singleDescendant", hangup_id)
    _text(module, "moduleName", f"TransferTo{_safe_fragment(option['label'])}")
    _text(module, "locationX", 650 if x is None else x)
    _text(module, "locationY", (110 + int(option["digit"]) * 70 if option["digit"].isdigit() else 320) if y is None else y)
    _text(module, "moduleId", option["module_id"])

    data = ET.SubElement(module, "data")
    _append_dispo(data, "0", "No Disposition")
    _text(data, "maxQueueTime", "600")
    _text(data, "queueIfOnCall", "true")
    _text(data, "onCallQueueTime", "600")
    _text(data, "queueIfOnBreakOrLoggedOut", "true")
    _text(data, "onBreakOrLoggedOutQueueTime", "600")
    _text(data, "onQueueTimeoutExpiration", "Hangup")
    _text(data, "pauseBeforeTransfer", "0")
    _text(data, "maxRingTime", "30")
    _text(data, "placeOnBreakIfNoAnswer", "false")
    _text(data, "vmTransferOnQueueTimeout", "false")
    _text(data, "vmTransferOnDigit", "")
    _text(data, "vmBoxType", "SKILL")
    _text(data, "clearDigitBuffer", "true")
    _text(data, "enableMusicOnHold", "true")
    for ann_type in ("INITIAL", "PERIODIC", "EWT", "POSITION", "CALLBACK"):
        _append_announcement(data, ann_type)
    _text(data, "priorityChangeType", "NONE")
    priority = ET.SubElement(data, "priorityChangeValue")
    _text(priority, "isVarSelected", "false")
    integer_value = ET.SubElement(priority, "integerValue")
    _text(integer_value, "value", "0")
    skills = ET.SubElement(data, "listOfSkillsEx")
    skill = ET.SubElement(skills, "extrnalObj")
    _text(skill, "id", "0")
    _text(skill, "name", option["target"])
    _text(skills, "varSelected", "false")
    _text(data, "taskType", "CALL")
    transfer_algorithm = ET.SubElement(data, "transferAlgorithm")
    _text(transfer_algorithm, "algorithmType", "LONGEST_IDLE")
    _text(transfer_algorithm, "statAlgorithmTimeWindow", "0")


def append_hangup(
    modules: ET.Element,
    module_name: str,
    module_id: str,
    ascendants: list[str],
    x: int = 900,
    y: int = 180,
) -> None:
    module = ET.SubElement(modules, "hangup")
    for ascendant in ascendants:
        _text(module, "ascendants", ascendant)
    _text(module, "moduleName", module_name)
    _text(module, "locationX", x)
    _text(module, "locationY", y)
    _text(module, "moduleId", module_id)
    data = ET.SubElement(module, "data")
    _append_dispo(data, "0", "No Disposition")
    _text(data, "returnToCallingModule", "true")
    err_code = ET.SubElement(data, "errCode")
    _text(err_code, "isVarSelected", "false")
    integer_value = ET.SubElement(err_code, "integerValue")
    _text(integer_value, "value", "0")
    err_description = ET.SubElement(data, "errDescription")
    _text(err_description, "isVarSelected", "false")
    string_value = ET.SubElement(err_description, "stringValue")
    _text(string_value, "value", "")
    _text(string_value, "id", "0")
    _text(data, "overwriteDisposition", "true")


def append_modules_on_hangup(root: ET.Element, start_id: str, hangup_id: str) -> None:
    modules = ET.SubElement(root, "modulesOnHangup")
    start = ET.SubElement(modules, "startOnHangup")
    _text(start, "singleDescendant", hangup_id)
    _text(start, "moduleName", "StartOnHangup1")
    _text(start, "locationX", "20")
    _text(start, "locationY", "10")
    _text(start, "moduleId", start_id)
    append_hangup(modules, "Hangup1", hangup_id, [start_id])
    modules.find("hangup/data/dispo/id").text = "-17"
    modules.find("hangup/data/dispo/name").text = "Caller Disconnected"
    modules.find("hangup/data/overwriteDisposition").text = "false"


def append_canvas_module(
    modules: ET.Element,
    module_type: str,
    module_id: str,
    label: str,
    config: Mapping[str, Any] | None,
    ascendants: list[str],
    outgoing_edges: list[Mapping[str, str]],
    x: int = 100,
    y: int = 100,
) -> None:
    if module_type in LOCKED_MODULE_TYPES:
        raise ValueError(f"{module_type} is locked until a real exported module shape exists")
    if module_type == "startOnHangup":
        raise ValueError("startOnHangup is compiler-owned inside modulesOnHangup")

    cfg = dict(config or {})
    module = ET.SubElement(modules, module_type)
    for ascendant in ascendants:
        _text(module, "ascendants", ascendant)

    if module_type in {"menu", "ifElse", "case", "answerMachine"}:
        pass
    elif module_type != "hangup" and outgoing_edges:
        _text(module, "singleDescendant", str(outgoing_edges[0]["target"]))

    _text(module, "moduleName", label or _display_label(module_type))
    _text(module, "locationX", x)
    _text(module, "locationY", y)
    _text(module, "moduleId", module_id)
    data = ET.SubElement(module, "data")
    _append_canvas_data(data, module_type, label, cfg, outgoing_edges)


def append_default_root_blocks(root: ET.Element, prompt_name: str = "Generated Prompt", prompt_text: str = "") -> None:
    ET.SubElement(root, "userVariables")
    append_prompt_catalog(root, {"prompt_name": prompt_name, "text": prompt_text}, "PROMPT_GENERATED")
    append_empty_language_blocks(root)
    for tag, value in (
        ("defaultLanguage", "en-US"),
        ("defaultMethod", "GET"),
        ("defaultFetchTimeout", "5"),
        ("showLabelNames", "true"),
        ("defaultVivrTimeout", "5"),
        ("unicodeEncoding", "true"),
        ("useShortcut", "false"),
        ("resetErrorCode", "false"),
        ("showAllChannelPrompts", "false"),
        ("extContactFieldsInput", "false"),
        ("extContactFieldsOutput", "false"),
        ("useIvrTimeZoneInAssignment", "false"),
        ("timeoutInMilliseconds", "3600000"),
        ("version", "1300001"),
    ):
        _text(root, tag, value)


def append_prompt_catalog(root: ET.Element, greeting: Mapping[str, Any], prompt_id: str) -> None:
    prompts = ET.SubElement(root, "multiLanguagesPrompts")
    entry = ET.SubElement(prompts, "entry")
    _text(entry, "key", prompt_id)
    value = ET.SubElement(entry, "value")
    _text(value, "promptId", prompt_id)
    _text(value, "name", str(greeting.get("prompt_name") or "Main Greeting"))
    _text(value, "description", str(greeting.get("text") or ""))
    _text(value, "type", "TTS")
    _text(value, "defaultLanguage", "en-US")
    _text(value, "isPersistent", "true")


def append_empty_language_blocks(root: ET.Element) -> None:
    for tag in (
        "multiLanguagesVIVRPrompts",
        "multiLanguagesTextPrompts",
        "multiLanguagesMenuChoices",
        "multiLanguagesEwtAnnouncement",
        "languages",
        "functions",
    ):
        ET.SubElement(root, tag)


def _append_tts_prompt(parent: ET.Element, text: str, name: str) -> None:
    tts = ET.SubElement(parent, "ttsPrompt")
    _text(tts, "xml", f"<speak>{text}</speak>" if text else "")
    enumed = ET.SubElement(tts, "promptTTSEnumed")
    _text(enumed, "id", "0")
    _text(enumed, "name", name)


def _append_prompt_flags(parent: ET.Element) -> None:
    _text(parent, "interruptible", "true")
    _text(parent, "canChangeInterruptableOption", "true")
    _text(parent, "ttsEnumed", "true")
    _text(parent, "exitModuleOnException", "false")


def _append_query_prompt_flags(parent: ET.Element) -> None:
    _text(parent, "interruptible", "false")
    _text(parent, "canChangeInterruptableOption", "true")
    _text(parent, "ttsEnumed", "false")
    _text(parent, "exitModuleOnException", "false")


def _append_query_empty_prompt_block(parent: ET.Element, tag: str) -> None:
    block = ET.SubElement(parent, tag)
    _append_query_prompt_flags(block)


def _append_query_text_channel_data(parent: ET.Element) -> None:
    text_channel = ET.SubElement(parent, "textChannelData")
    text_prompts = ET.SubElement(text_channel, "textPrompts")
    _append_query_prompt_flags(text_prompts)
    _text(text_channel, "isUsedVivrPrompts", "true")
    _text(text_channel, "isTextOnly", "true")


def _append_empty_prompt_block(parent: ET.Element, tag: str) -> None:
    block = ET.SubElement(parent, tag)
    _append_prompt_flags(block)


def _append_text_channel_data(parent: ET.Element) -> None:
    text_channel = ET.SubElement(parent, "textChannelData")
    text_prompts = ET.SubElement(text_channel, "textPrompts")
    _append_prompt_flags(text_prompts)
    _text(text_channel, "isUsedVivrPrompts", "false")
    _text(text_channel, "isTextOnly", "false")


def _append_email_prompt(parent: ET.Element, tag: str) -> None:
    block = ET.SubElement(parent, tag)
    _append_empty_prompt_block(block, "vivrPrompt")
    _append_prompt_flags(block)


def _append_dispo(parent: ET.Element, dispo_id: str, name: str) -> None:
    dispo = ET.SubElement(parent, "dispo")
    _text(dispo, "id", dispo_id)
    _text(dispo, "name", name)


def _append_branch(parent: ET.Element, key: str, name: str, target_id: str) -> None:
    entry = ET.SubElement(parent, "entry")
    _text(entry, "key", key)
    value = ET.SubElement(entry, "value")
    _text(value, "name", name)
    _text(value, "desc", target_id)


def _append_recognition_event(parent: ET.Element, event_name: str) -> None:
    event = ET.SubElement(parent, "recoEvents")
    _text(event, "event", event_name)
    _text(event, "count", "1")
    compound = ET.SubElement(event, "compoundPrompt")
    ET.SubElement(compound, "multiLanguagesPromptItem")
    _append_prompt_flags(compound)
    _text(event, "action", "REPEAT")


def _append_menu_prompt_count(parent: ET.Element) -> None:
    prompts = ET.SubElement(parent, "prompts")
    prompt = ET.SubElement(prompts, "prompt")
    ET.SubElement(prompt, "ttsPrompt")
    ET.SubElement(prompt, "filePrompt")
    _append_prompt_flags(prompt)
    _text(prompts, "count", "1")


def _append_confirm_data(parent: ET.Element) -> None:
    confirm = ET.SubElement(parent, "confirmData")
    _text(confirm, "confirmRequired", "false")
    _text(confirm, "requiredConfidence", "50")
    _text(confirm, "maxAttemptsToConfirm", "1")
    _text(confirm, "noInputTimeout", "5")
    _text(confirm, "maxTimeToEnter", "5")
    _text(confirm, "completeTimeout", "1")
    _text(confirm, "confidenceTreshold", "50")
    _text(confirm, "sensitivity", "50")
    _text(confirm, "incompleteTimeout", "1")
    _text(confirm, "swirecNbestListLength", "1")
    _append_recognize_config_parameters(confirm)
    prompt = ET.SubElement(confirm, "prompt")
    ET.SubElement(prompt, "multiLanguagesPromptItem")
    _append_prompt_flags(prompt)
    _append_recognition_event(confirm, "NO_MATCH")
    _append_recognition_event(confirm, "NO_INPUT")


def _append_recognize_config_parameters(parent: ET.Element) -> None:
    params = ET.SubElement(parent, "recognizeConfigParameters")
    for name, value in (
        ("confidencelevel", "50"),
        ("sensitivity", "50"),
        ("speedvsaccuracy", "50"),
        ("completetimeout", "1"),
    ):
        param = ET.SubElement(params, "recognizeConfigParameter")
        _text(param, "name", name)
        _text(param, "value", value)


def _append_announcement(parent: ET.Element, ann_type: str) -> None:
    ann = ET.SubElement(parent, "announcements")
    _text(ann, "enabled", "false")
    _text(ann, "loopped", "false")
    _text(ann, "timeout", "0")
    ET.SubElement(ann, "prompt")
    _text(ann, "annType", ann_type)


def _append_canvas_data(
    data: ET.Element,
    module_type: str,
    label: str,
    config: Mapping[str, Any],
    outgoing_edges: list[Mapping[str, str]],
) -> None:
    if module_type == "incomingCall":
        return
    if module_type == "play":
        prompt = ET.SubElement(data, "prompt")
        _append_tts_prompt(prompt, str(config.get("text") or ""), str(config.get("prompt_name") or label or "Prompt"))
        _append_prompt_flags(prompt)
        _append_dispo(data, "0", "No Disposition")
        _append_empty_prompt_block(data, "vivrPrompts")
        _append_empty_prompt_block(data, "vivrHeader")
        _append_text_channel_data(data)
        _text(data, "numberOfDigits", config.get("numberOfDigits", "0"))
        _text(data, "terminateDigit", config.get("terminateDigit", ""))
        _text(data, "clearDigitBuffer", "false")
        _text(data, "collapsible", "false")
        return
    if module_type == "menu":
        _append_dispo(data, "0", "No Disposition")
        branches = ET.SubElement(data, "branches")
        for edge in outgoing_edges:
            label_value = str(edge.get("label") or edge.get("branch") or "Next")
            _append_branch(branches, label_value, label_value, str(edge["target"]))
        _text(data, "useSpeechRecognition", str(config.get("useSpeechRecognition", "false")).lower())
        _text(data, "useDTMF", str(config.get("useDTMF", "true")).lower())
        _text(data, "maxAttempts", config.get("maxAttempts", "3"))
        _text(data, "maxTimeToEnter", config.get("maxTimeToEnter", "5"))
        _text(data, "noInputTimeout", config.get("noInputTimeout", "5"))
        _append_recognize_config_parameters(data)
        return
    if module_type == "skillTransfer":
        option = {
            "label": label or str(config.get("target") or "Skill"),
            "target": str(config.get("target") or config.get("skill") or label or "Sales"),
            "module_id": "unused",
            "digit": "0",
        }
        _append_dispo(data, "0", "No Disposition")
        _text(data, "maxQueueTime", config.get("maxQueueTime", "600"))
        _text(data, "queueIfOnCall", "true")
        _text(data, "onCallQueueTime", "600")
        _text(data, "queueIfOnBreakOrLoggedOut", "true")
        _text(data, "onBreakOrLoggedOutQueueTime", "600")
        _text(data, "onQueueTimeoutExpiration", "Hangup")
        _text(data, "pauseBeforeTransfer", "0")
        _text(data, "maxRingTime", "30")
        _text(data, "clearDigitBuffer", "true")
        _text(data, "enableMusicOnHold", "true")
        skills = ET.SubElement(data, "listOfSkillsEx")
        skill = ET.SubElement(skills, "extrnalObj")
        _text(skill, "id", "0")
        _text(skill, "name", option["target"])
        _text(skills, "varSelected", "false")
        transfer_algorithm = ET.SubElement(data, "transferAlgorithm")
        _text(transfer_algorithm, "algorithmType", "LONGEST_IDLE")
        _text(transfer_algorithm, "statAlgorithmTimeWindow", "0")
        return
    if module_type == "hangup":
        _append_dispo(data, "0", "No Disposition")
        _text(data, "returnToCallingModule", "true")
        _text(data, "overwriteDisposition", "true")
        return
    if module_type == "setVariable":
        expressions = ET.SubElement(data, "expressions")
        _text(expressions, "variableName", config.get("variableName", "generatedVar"))
        _text(expressions, "isFunction", "false")
        constant = ET.SubElement(expressions, "constant")
        _text(constant, "isVarSelected", "false")
        string_value = ET.SubElement(constant, "stringValue")
        _text(string_value, "value", config.get("value", "value"))
        _text(string_value, "id", "0")
        return
    if module_type in {"ifElse", "case", "answerMachine"}:
        branches = ET.SubElement(data, "branches")
        if outgoing_edges:
            for edge in outgoing_edges:
                label_value = str(edge.get("label") or "Next")
                _append_branch(branches, label_value, label_value, str(edge["target"]))
        else:
            _append_branch(branches, "ELSE", "ELSE", "")
        _text(data, "condition", config.get("condition", "true"))
        return
    if module_type == "getDigits":
        _text(data, "targetVariableName", config.get("targetVariableName") or config.get("variableName") or "digits")
        _text(data, "numberOfDigits", config.get("numberOfDigits") or config.get("maxDigits") or "1")
        _text(data, "maxTime", config.get("maxTime", "5"))
        _text(data, "maxSilence", config.get("maxSilence", "2"))
        _text(data, "terminateDigit", config.get("terminateDigit", "#"))
        _text(data, "clearDigitBuffer", "false")
        _append_dispo(data, "0", "No Disposition")
        return
    if module_type == "query":
        _append_query_empty_prompt_block(data, "prompt")
        _append_query_empty_prompt_block(data, "vivrPrompts")
        _append_query_empty_prompt_block(data, "vivrHeader")
        _append_query_text_channel_data(data)
        _text(data, "url", config.get("url", "https://example.com/five9-certification"))
        _text(data, "method", config.get("method", "GET"))
        _text(data, "fetchTimeout", config.get("fetchTimeout", "5"))
        ET.SubElement(data, "parameters")
        ET.SubElement(data, "returnValues")
        _text(data, "storeNumberOfArrayElementsInVariable", "false")
        request_info = ET.SubElement(data, "requestInfo")
        template = ET.SubElement(request_info, "template")
        _text(template, "base64", config.get("requestTemplateBase64", "H4sIAAAAAAAAAAMAAAAAAAAAAAA="))
        ET.SubElement(data, "headers")
        _text(data, "requestBodyType", config.get("requestBodyType", "LIST"))
        response_info = ET.SubElement(data, "responseInfos")
        _text(response_info, "from", config.get("successStatusFrom", "200"))
        _text(response_info, "to", config.get("successStatusTo", "200"))
        _text(response_info, "method", "REG_EXP")
        regexp = ET.SubElement(response_info, "regexp")
        _text(regexp, "regexp", config.get("responseRegexp", ""))
        _text(regexp, "regexpFlags", config.get("regexpFlags", "0"))
        _text(data, "saveStatusCode", str(config.get("saveStatusCode", "false")).lower())
        if config.get("saveStatusCode") is True and config.get("saveStatusCodeVar"):
            _text(data, "saveStatusCodeVar", config.get("saveStatusCodeVar"))
        _text(data, "saveReasonPhrase", str(config.get("saveReasonPhrase", "false")).lower())
        if config.get("saveReasonPhrase") is True and config.get("saveReasonPhraseVar"):
            _text(data, "saveReasonPhraseVar", config.get("saveReasonPhraseVar"))
        return
    if module_type == "foreignScript":
        _text(data, "ivrScript", config.get("ivrScript") or config.get("scriptName") or "Referenced Script")
        ET.SubElement(data, "params")
        ET.SubElement(data, "returnVals")
        _text(data, "passCRM", "false")
        _text(data, "returnCRM", "false")
        _text(data, "isConsistent", "true")
        return
    if module_type in {"voiceMailTransfer", "thirdPartyTransfer", "agentTransfer", "extensionTransfer", "ivaTransfer"}:
        transfer_target = config.get("target") or config.get("destination") or label or module_type
        _text(data, "target", transfer_target)
        _text(data, "clearDigitBuffer", "true")
        _append_dispo(data, "0", "No Disposition")
        return
    if module_type == "language":
        _text(data, "selectionMode", config.get("selectionMode", "DEFAULT"))
        items = ET.SubElement(data, "items")
        item = ET.SubElement(items, "item")
        _text(item, "language", config.get("language", "en-US"))
        return
    if module_type == "input":
        _text(data, "grammar", config.get("grammar", "builtin:dtmf/digits"))
        _text(data, "targetVariableName", config.get("targetVariableName", "input"))
        _append_recognition_event(data, "NO_MATCH")
        _append_recognition_event(data, "NO_INPUT")
        return
    if module_type == "recording":
        _text(data, "varToAccessRecording", config.get("varToAccessRecording", "recordingUrl"))
        _text(data, "maxTime", config.get("maxTime", "60"))
        _text(data, "finalSilence", config.get("finalSilence", "3"))
        _text(data, "DTMFtermination", config.get("DTMFtermination", "#"))
        return
    if module_type == "iterator":
        _text(data, "mode", config.get("mode", "LIST"))
        _text(data, "operation", config.get("operation", "NEXT"))
        _text(data, "collection", config.get("collection", "items"))
        return
    if module_type == "lookupCRMRecord":
        _text(data, "lookupCriteria", config.get("lookupCriteria", "ANI"))
        ET.SubElement(data, "conditions")
        return
    if module_type == "crmUpdate":
        _text(data, "mode", config.get("mode", "UPDATE"))
        ET.SubElement(data, "selectedFields")
        return
    if module_type == "systemInfo":
        _text(data, "systemInfoType", config.get("systemInfoType", "CALL"))
        ET.SubElement(data, "targetResultVariableNames")
        return
    if module_type == "systemUpdate":
        _text(data, "objectToModify", config.get("objectToModify", "CALL"))
        ET.SubElement(data, "fieldsToModify")
        return
    if module_type == "setDNC":
        _text(data, "targetVariableName", config.get("targetVariableName", "ani"))
        _text(data, "dncOperation", config.get("dncOperation", "ADD"))
        return
    if module_type == "conference":
        _text(data, "maxNumberOfParticipants", config.get("maxNumberOfParticipants", "3"))
        _text(data, "destination", config.get("destination", ""))
        return
    _text(data, "compilerCandidate", "true")


def _display_label(module_type: str) -> str:
    label = module_type[:1].upper() + module_type[1:]
    return label.replace("IVR", "IVR")


def _safe_fragment(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.strip())
    return cleaned.strip("_") or "Route"


def _text(parent: ET.Element, tag: str, value: Any) -> ET.Element:
    child = ET.SubElement(parent, tag)
    child.text = str(value)
    return child
