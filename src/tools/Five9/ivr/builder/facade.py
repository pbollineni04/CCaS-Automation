from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime
from hashlib import sha1
from pathlib import Path
import re
from typing import Any, Mapping
from xml.dom import minidom
from xml.etree import ElementTree as ET

from . import block_registry as ivr_blocks


BUILD_PLAN_SCHEMA = "five9_simple_menu_ivr_v1"
CANVAS_SCHEMA = "five9_ivr_canvas_v1"
CERTIFICATION_TARGET_SCRIPT = "ZZ_TEST_Codex_IVR_ModuleLab"
SUPPORTED_TRANSFER_TYPES = {"skill", "campaign"}
SUPPORTED_FALLBACKS = {"hangup"}
DEFAULT_ALL_MODULES_EXPORT = Path(r"C:\Users\jrgoo\Desktop\All Modules.five9ivr")
DEFAULT_IVR_EXPORT_FOLDER = Path(r"C:\Five9 IVR")

SAMPLE_BUILD_PLAN: dict[str, Any] = {
    "script_name": "Acme Main IVR",
    "description": "Main inbound IVR",
    "greeting": {
        "prompt_name": "Main Greeting",
        "text": "Thank you for calling Acme Health Services.",
    },
    "menu": {
        "name": "Main Menu",
        "options": [
            {"digit": "1", "label": "Sales", "transfer_type": "skill", "target": "Sales"},
            {"digit": "2", "label": "Billing", "transfer_type": "skill", "target": "Billing"},
            {"digit": "3", "label": "Support", "transfer_type": "skill", "target": "Support"},
        ],
        "no_match": "hangup",
        "no_input": "hangup",
    },
}

MODULE_CATALOG: dict[str, dict[str, Any]] = {
    "incomingCall": {
        "generation_status": "supported_v1",
        "required_fields": ["moduleName", "moduleId", "singleDescendant"],
        "output_behavior": "Entry point for the IVR graph.",
        "example": "START_Acme_Main_IVR -> Greeting",
    },
    "play": {
        "generation_status": "supported_v1",
        "required_fields": ["moduleName", "moduleId", "singleDescendant", "prompt"],
        "output_behavior": "Plays the configured greeting prompt before menu routing.",
        "example": "Greeting -> Main Menu",
    },
    "menu": {
        "generation_status": "supported_v1",
        "required_fields": ["name", "digit", "label", "target"],
        "optional_fields": ["no_match", "no_input"],
        "output_behavior": "Branches DTMF choices to transfer modules.",
        "example": "1 -> Sales skillTransfer, 2 -> Billing skillTransfer",
    },
    "skillTransfer": {
        "generation_status": "supported_v1",
        "required_fields": ["target"],
        "output_behavior": "Transfers the caller to a named Five9 skill.",
        "example": "target=Sales",
    },
    "campaignTransfer": {
        "generation_status": "supported_v1",
        "required_fields": ["target"],
        "output_behavior": "Transfers the caller to a named Five9 campaign.",
        "example": "target=Billing Inbound",
    },
    "hangup": {
        "generation_status": "supported_v1",
        "required_fields": ["moduleName", "moduleId"],
        "output_behavior": "Terminates the call flow.",
        "example": "No Match -> Hangup",
    },
    "setVariable": {
        "generation_status": "documented_only",
        "required_fields": ["variableName", "value"],
        "output_behavior": "Sets IVR runtime variables; parsed but not generated in v1.",
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
        "required_fields": ["scriptName"],
        "output_behavior": "Calls another IVR script; parsed but not generated in v1.",
    },
    "input": {
        "generation_status": "documented_only",
        "required_fields": ["variableName"],
        "output_behavior": "Collects caller digits; parsed but not generated in v1.",
    },
    "getDigits": {
        "generation_status": "documented_only",
        "required_fields": ["variableName", "maxDigits"],
        "output_behavior": "Collects DTMF digits; parsed but not generated in v1.",
    },
    "agentTransfer": {
        "generation_status": "documented_only",
        "required_fields": ["agent"],
        "output_behavior": "Transfers caller to a specific agent; parsed but not generated in v1.",
    },
    "extensionTransfer": {
        "generation_status": "documented_only",
        "required_fields": ["extension"],
        "output_behavior": "Transfers caller to an extension; parsed but not generated in v1.",
    },
    "thirdPartyTransfer": {
        "generation_status": "documented_only",
        "required_fields": ["destination"],
        "output_behavior": "Transfers to an external destination; parsed but not generated in v1.",
    },
    "voiceMailTransfer": {
        "generation_status": "documented_only",
        "required_fields": ["mailbox"],
        "output_behavior": "Transfers caller to voicemail; parsed but not generated in v1.",
    },
    "voicemailTransfer": {
        "generation_status": "documented_only",
        "required_fields": ["mailbox"],
        "output_behavior": "Transfers caller to voicemail; parsed but not generated in v1.",
    },
    "ivaTransfer": {
        "generation_status": "documented_only",
        "required_fields": ["application"],
        "output_behavior": "Transfers caller to IVA/NLP handling; parsed but not generated in v1.",
    },
    "answerMachine": {
        "generation_status": "documented_only",
        "required_fields": ["livePerson", "answerMachine"],
        "output_behavior": "Branches based on answering machine detection; parsed but not generated in v1.",
    },
    "language": {
        "generation_status": "documented_only",
        "required_fields": ["language"],
        "output_behavior": "Sets or selects IVR language; parsed but not generated in v1.",
    },
    "lookupCRMRecord": {
        "generation_status": "documented_only",
        "required_fields": ["crmObject"],
        "output_behavior": "Looks up a CRM record; parsed but not generated in v1.",
    },
    "crmUpdate": {
        "generation_status": "documented_only",
        "required_fields": ["crmObject"],
        "output_behavior": "Updates a CRM record; parsed but not generated in v1.",
    },
    "systemInfo": {
        "generation_status": "documented_only",
        "required_fields": ["field"],
        "output_behavior": "Reads Five9/system runtime data; parsed but not generated in v1.",
    },
    "systemUpdate": {
        "generation_status": "documented_only",
        "required_fields": ["field", "value"],
        "output_behavior": "Updates Five9/system runtime data; parsed but not generated in v1.",
    },
    "iterator": {
        "generation_status": "documented_only",
        "required_fields": ["collection"],
        "output_behavior": "Iterates over a collection; parsed but not generated in v1.",
    },
    "setDNC": {
        "generation_status": "documented_only",
        "required_fields": ["number"],
        "output_behavior": "Sets Do Not Call state; parsed but not generated in v1.",
    },
    "conference": {
        "generation_status": "documented_only",
        "required_fields": ["destination"],
        "output_behavior": "Starts a conference call leg; parsed but not generated in v1.",
    },
    "recording": {
        "generation_status": "documented_only",
        "required_fields": ["recording_action"],
        "output_behavior": "Controls call recording; parsed but not generated in v1.",
    },
}


MODULE_CATALOG = ivr_blocks.registry_copy()


def get_ivr_builder_catalog() -> dict[str, Any]:
    return {
        "build_plan_schema": BUILD_PLAN_SCHEMA,
        "canvas_schema": CANVAS_SCHEMA,
        "module_manual": (
            "AI must produce the normalized build plan JSON. The compiler uses sanitized "
            "building blocks derived from real Five9 XML exports; raw customer exports and "
            "raw XML authoring are not app-facing inputs in v1."
        ),
        "supported_v1_shape": "incomingCall -> play greeting -> menu -> skill transfer -> hangup",
        "canvas_model": "nodes[id,module_type,label,position,config] + edges[source,target,label]",
        "certification_target_script": CERTIFICATION_TARGET_SCRIPT,
        "modules": deepcopy(MODULE_CATALOG),
        "constraints": [
            "Canvas compiler can generate observed corpus-backed module candidates.",
            "Live deployment of uncertified candidate modules should go through certification mode first.",
            "V1 supports skillTransfer only; campaignTransfer is blocked until a real export proves its XML shape.",
            "Raw client export files are reference material only and are not app-facing runtime inputs.",
            "Live Five9 updates must use the approval-gated deploy endpoint.",
        ],
        "sample_build_plan": deepcopy(SAMPLE_BUILD_PLAN),
    }


def get_ivr_builder_palette(file_path: str | None = None, folder_path: str | None = None) -> dict[str, Any]:
    if not file_path and not folder_path:
        source = None
    elif folder_path:
        source = Path(folder_path).expanduser()
    else:
        source = Path(file_path).expanduser()
    palette_source = "builtin_registry"
    discovered: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []

    if source is not None and source.exists() and source.is_dir():
        parsed_count = 0
        for ivr_file in sorted(source.glob("*.five9ivr")):
            try:
                palette = analyze_module_palette_file(str(ivr_file))
                _merge_palette_catalog(discovered, palette.get("catalog", {}))
                parsed_count += 1
            except ValueError as exc:
                warnings.append(f"{ivr_file.name}: {exc}")
        if parsed_count:
            palette_source = str(source)
            warnings.append(f"Loaded module examples from {parsed_count} IVR export file(s)")
        else:
            warnings.append(f"No .five9ivr files found in folder: {source}")
    elif source is not None and source.exists() and source.is_file():
        try:
            palette = analyze_module_palette_file(str(source))
            palette_source = str(source)
            discovered = palette.get("catalog", {})
            warnings.extend(palette.get("warnings", []))
        except ValueError as exc:
            warnings.append(str(exc))
    elif file_path or folder_path:
        warnings.append(f"IVR module palette source does not exist: {source}")

    module_types = sorted(set(MODULE_CATALOG) | set(discovered), key=lambda value: (_module_group(value), value.lower()))
    entries: list[dict[str, Any]] = []
    for module_type in module_types:
        builtin = MODULE_CATALOG.get(module_type, {})
        export_info = discovered.get(module_type, {})
        generation_status = builtin.get("generation_status", "documented_only")
        supported = generation_status in {"supported_v1", "compiler_candidate"}
        locked = generation_status == "unsupported_no_corpus_evidence"
        status_label = (
            "Compiler-supported"
            if generation_status == "supported_v1"
            else "Compiler candidate; live certification pending"
            if generation_status == "compiler_candidate"
            else "Not compiler-supported yet"
        )
        entries.append(
            {
                "module_type": module_type,
                "label": _module_display_label(module_type),
                "group": _module_group(module_type),
                "generation_status": generation_status,
                "supported": supported,
                "locked": locked,
                "locked_reason": ""
                if not locked
                else "No real exported Five9 module shape is available for this block.",
                "status_label": status_label,
                "certification": deepcopy(builtin.get("certification", {})),
                "source": "export" if module_type in discovered else "builtin",
                "examples": deepcopy(export_info.get("examples", [])),
                "data_fields": deepcopy(export_info.get("data_fields", [])),
                "connection_fields": deepcopy(export_info.get("connection_fields", [])),
                "required_fields": deepcopy(builtin.get("required_fields", [])),
                "optional_fields": deepcopy(builtin.get("optional_fields", [])),
                "output_behavior": builtin.get("output_behavior", "Discovered from Five9 IVR export."),
            }
        )

    return {
        "build_plan_schema": BUILD_PLAN_SCHEMA,
        "palette_source": palette_source,
        "warnings": warnings,
        "modules": entries,
        "supported_module_types": [entry["module_type"] for entry in entries if entry["supported"]],
        "locked_module_types": [entry["module_type"] for entry in entries if entry["locked"]],
    }


def visualize_build_plan(build_plan: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_build_plan(build_plan)
    palette = get_ivr_builder_palette()["modules"]
    if not validation["valid"]:
        return {
            "build_plan_schema": BUILD_PLAN_SCHEMA,
            "valid": False,
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "nodes": [],
            "edges": [],
            "palette": palette,
            "required_preflight_objects": validation["required_preflight_objects"],
        }

    script_name = _clean_string(build_plan["script_name"])
    greeting = build_plan["greeting"]
    menu = build_plan["menu"]
    options = menu["options"]
    layout = _layout_map(build_plan)
    incoming_pos = _node_position(layout, "incoming", 40, 160)
    greeting_pos = _node_position(layout, "greeting", 260, 160)
    menu_pos = _node_position(layout, "menu", 500, 160)
    hangup_pos = _node_position(layout, "hangup", 1010, 160)

    nodes: list[dict[str, Any]] = [
        {
            "id": "incoming",
            "module_type": "incomingCall",
            "label": "Incoming Call",
            "subtitle": script_name,
            "x": incoming_pos[0],
            "y": incoming_pos[1],
            "locked": False,
        },
        {
            "id": "greeting",
            "module_type": "play",
            "label": "Play Greeting",
            "subtitle": _clean_string(greeting.get("prompt_name")),
            "text": _clean_string(greeting.get("text")),
            "x": greeting_pos[0],
            "y": greeting_pos[1],
            "locked": False,
        },
        {
            "id": "menu",
            "module_type": "menu",
            "label": _clean_string(menu.get("name")),
            "subtitle": f"{len(options)} option(s)",
            "x": menu_pos[0],
            "y": menu_pos[1],
            "locked": False,
        },
    ]
    edges: list[dict[str, str]] = [
        {"id": "edge_incoming_greeting", "from": "incoming", "to": "greeting", "label": ""},
        {"id": "edge_greeting_menu", "from": "greeting", "to": "menu", "label": ""},
    ]

    for index, option in enumerate(options):
        node_id = f"transfer_{_clean_string(option.get('digit'))}"
        module_type = "skillTransfer" if option["transfer_type"] == "skill" else "campaignTransfer"
        transfer_pos = _node_position(layout, node_id, 750, 70 + index * 120)
        nodes.append(
            {
                "id": node_id,
                "module_type": module_type,
                "label": _clean_string(option.get("label")),
                "subtitle": f"{option['transfer_type']}: {option['target']}",
                "digit": _clean_string(option.get("digit")),
                "target": _clean_string(option.get("target")),
                "transfer_type": _clean_string(option.get("transfer_type")),
                "x": transfer_pos[0],
                "y": transfer_pos[1],
                "locked": False,
            }
        )
        edges.append(
            {
                "id": f"edge_menu_{node_id}",
                "from": "menu",
                "to": node_id,
                "label": _clean_string(option.get("digit")),
            }
        )
        edges.append(
            {
                "id": f"edge_{node_id}_hangup",
                "from": node_id,
                "to": "hangup",
                "label": "success",
            }
        )

    nodes.append(
        {
            "id": "hangup",
            "module_type": "hangup",
            "label": "Hangup",
            "subtitle": "No Match / No Input / transfer complete",
            "x": hangup_pos[0],
            "y": hangup_pos[1],
            "locked": False,
        }
    )
    edges.extend(
        [
            {"id": "edge_menu_hangup_no_match", "from": "menu", "to": "hangup", "label": "No Match"},
            {"id": "edge_menu_hangup_no_input", "from": "menu", "to": "hangup", "label": "No Input"},
        ]
    )

    return {
        "build_plan_schema": BUILD_PLAN_SCHEMA,
        "valid": True,
        "errors": [],
        "warnings": validation["warnings"],
        "nodes": nodes,
        "edges": edges,
        "palette": palette,
        "required_preflight_objects": validation["required_preflight_objects"],
    }


def validate_visual_canvas(canvas: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(canvas, Mapping):
        return _visual_canvas_result(False, ["canvas must be an object"], [], {})
    if "nodes" in canvas and "edges" in canvas and "build_plan" not in canvas:
        validation = validate_canvas_model(canvas)
        return {
            "build_plan_schema": BUILD_PLAN_SCHEMA,
            "canvas_schema": CANVAS_SCHEMA,
            "valid": validation["valid"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "required_preflight_objects": validation["required_preflight_objects"],
            "canvas": validation["canvas"],
            "metadata": validation["metadata"],
        }
    nodes = canvas.get("nodes", [])
    if not isinstance(nodes, list):
        return _visual_canvas_result(False, ["canvas.nodes must be a list"], [], {})

    unsupported = [
        _clean_string(node.get("module_type"))
        for node in nodes
        if isinstance(node, Mapping)
        and _clean_string(node.get("zone", "main")) in {"main", "main_flow"}
        and MODULE_CATALOG.get(_clean_string(node.get("module_type")), {}).get("generation_status") != "supported_v1"
    ]
    if unsupported:
        return _visual_canvas_result(
            False,
            [f"Unsupported module in deployable flow: {module_type}" for module_type in unsupported],
            ["Remove unsupported modules from Main Flow or leave them as reference-only."],
            {},
        )

    build_plan = canvas.get("build_plan")
    if isinstance(build_plan, Mapping):
        validation = validate_build_plan(build_plan)
        return _visual_canvas_result(
            validation["valid"],
            validation["errors"],
            validation["warnings"],
            validation["required_preflight_objects"],
            build_plan=build_plan if validation["valid"] else {},
        )

    return _visual_canvas_result(False, ["canvas.build_plan is required for V1 compile"], [], {})


def visual_canvas_to_build_plan(canvas: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_visual_canvas(canvas)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))
    return {
        "build_plan_schema": BUILD_PLAN_SCHEMA,
        "build_plan": deepcopy(validation["build_plan"]),
        "validation": validation,
    }


def parse_ivr_xml(xml_definition: str, script_name: str | None = None) -> dict[str, Any]:
    xml_text = _require_xml_text(xml_definition)
    root = ET.fromstring(xml_text)
    if root.tag != "ivrScript":
        raise ValueError("Expected root element <ivrScript>")

    modules_parent = root.find("modules")
    modules = list(modules_parent) if modules_parent is not None else []
    module_summaries = [_summarize_module(module) for module in modules]
    edges = _extract_edges(modules)

    return {
        "script_name": script_name or "",
        "root": root.tag,
        "version": root.findtext("version") or "",
        "default_language": root.findtext("defaultLanguage") or "",
        "module_counts": dict(Counter(module.tag for module in modules)),
        "modules": module_summaries,
        "edges": edges,
        "branches": _extract_branches(modules),
        "variables": _extract_user_variables(root),
        "prompts": _extract_prompts(root),
        "transfer_targets": _extract_transfer_targets(modules),
        "queries": _extract_queries(modules),
    }


def analyze_ivr_file(file_path: str) -> dict[str, Any]:
    path = Path(file_path).expanduser()
    if not path.exists() or not path.is_file():
        raise ValueError(f"IVR file does not exist: {file_path}")
    return parse_ivr_xml(path.read_text(encoding="utf-8-sig"), script_name=path.stem)


def analyze_ivr_export_folder(folder_path: str) -> list[dict[str, Any]]:
    folder = Path(folder_path).expanduser()
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"IVR export folder does not exist: {folder_path}")
    return [analyze_ivr_file(str(path)) for path in sorted(folder.glob("*.five9ivr"))]


def analyze_module_palette(xml_definition: str, script_name: str | None = None) -> dict[str, Any]:
    summary = parse_ivr_xml(xml_definition, script_name=script_name)
    catalog: dict[str, dict[str, Any]] = {}
    unconnected_modules: list[str] = []

    for module in summary["modules"]:
        module_type = module["module_type"]
        entry = catalog.setdefault(
            module_type,
            {
                "module_type": module_type,
                "generation_status": MODULE_CATALOG.get(module_type, {}).get("generation_status", "documented_only"),
                "examples": [],
                "data_fields": [],
                "connection_fields": [],
            },
        )
        if module["module_name"] and module["module_name"] not in entry["examples"]:
            entry["examples"].append(module["module_name"])
        entry["data_fields"] = sorted(set(entry["data_fields"]) | set(module["data_fields"]))
        entry["connection_fields"] = sorted(set(entry["connection_fields"]) | set(module["connection_fields"]))
        if module["connection_status"] == "unconnected" and module_type not in unconnected_modules:
            unconnected_modules.append(module_type)

    warnings: list[str] = []
    if not summary["edges"]:
        warnings.append("No executable main-flow edges were found")
    if unconnected_modules:
        warnings.append("Palette contains unconnected modules and should not be deployed")

    return {
        "script_name": summary["script_name"],
        "root": summary["root"],
        "module_count": len(summary["modules"]),
        "module_counts": summary["module_counts"],
        "deployable": bool(summary["edges"]) and not unconnected_modules,
        "warnings": warnings,
        "catalog": catalog,
        "unconnected_modules": unconnected_modules,
    }


def analyze_module_palette_file(file_path: str) -> dict[str, Any]:
    path = Path(file_path).expanduser()
    if not path.exists() or not path.is_file():
        raise ValueError(f"IVR file does not exist: {file_path}")
    return analyze_module_palette(path.read_text(encoding="utf-8-sig"), script_name=path.stem)


def analyze_module_library(folder_path: str | None = None) -> dict[str, Any]:
    folder = Path(folder_path).expanduser() if folder_path else DEFAULT_IVR_EXPORT_FOLDER
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"IVR export folder does not exist: {folder}")

    scripts: list[dict[str, Any]] = []
    modules: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, str]] = []

    for path in sorted(folder.glob("*.five9ivr")):
        try:
            summary = analyze_ivr_file(str(path))
        except ValueError as exc:
            errors.append({"file": str(path), "error": str(exc)})
            continue

        scripts.append(
            {
                "name": summary["script_name"],
                "file": str(path),
                "module_count": len(summary["modules"]),
                "edge_count": len(summary["edges"]),
                "module_counts": summary["module_counts"],
            }
        )
        for module in summary["modules"]:
            _add_module_manual_observation(
                modules,
                module,
                summary["script_name"],
                summary["edges"],
                summary["branches"],
                summary["transfer_targets"],
                summary["queries"],
            )

    manual_entries = [_finalize_module_manual_entry(entry) for entry in modules.values()]
    manual_entries.sort(key=lambda entry: (_module_group(entry["module_type"]), entry["module_type"].lower()))
    return {
        "folder": str(folder),
        "script_count": len(scripts),
        "failed_count": len(errors),
        "module_type_count": len(manual_entries),
        "scripts": scripts,
        "modules": manual_entries,
        "errors": errors,
        "summary": _build_module_library_summary(manual_entries),
    }


def validate_build_plan(build_plan: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required_skills: list[str] = []
    required_campaigns: list[str] = []
    required_prompts: list[str] = []

    if not isinstance(build_plan, Mapping):
        return _validation_result(False, ["build_plan must be an object"], warnings, {}, {}, {})

    if "modules" in build_plan or "xmlDefinition" in build_plan or "xml_definition" in build_plan:
        errors.append("raw module requests are not supported in v1")

    script_name = _clean_string(build_plan.get("script_name"))
    if not script_name:
        errors.append("script_name is required")

    greeting = build_plan.get("greeting")
    if not isinstance(greeting, Mapping):
        errors.append("greeting must be an object")
    else:
        prompt_name = _clean_string(greeting.get("prompt_name"))
        if not prompt_name:
            errors.append("greeting.prompt_name is required")
        else:
            required_prompts.append(prompt_name)
        if not _clean_string(greeting.get("text")):
            warnings.append("greeting.text is empty; prompt audio must already exist or be created separately")

    menu = build_plan.get("menu")
    options: list[Any] = []
    if not isinstance(menu, Mapping):
        errors.append("menu must be an object")
    else:
        if not _clean_string(menu.get("name")):
            errors.append("menu.name is required")
        raw_options = menu.get("options")
        if not isinstance(raw_options, list) or not raw_options:
            errors.append("menu.options must include at least one option")
        else:
            options = raw_options
        for fallback_name in ("no_match", "no_input"):
            fallback = _clean_string(menu.get(fallback_name, "hangup")) or "hangup"
            if fallback not in SUPPORTED_FALLBACKS:
                errors.append(f"unsupported {fallback_name}: {fallback}")

    seen_digits: set[str] = set()
    for option in options:
        if not isinstance(option, Mapping):
            errors.append("menu option must be an object")
            continue
        digit = _clean_string(option.get("digit"))
        label = _clean_string(option.get("label"))
        transfer_type = _clean_string(option.get("transfer_type"))
        target = _clean_string(option.get("target"))

        if not digit:
            errors.append("menu option digit is required")
        elif digit in seen_digits:
            errors.append(f"duplicate menu digit: {digit}")
        elif digit not in set("0123456789*#"):
            errors.append(f"unsupported menu digit: {digit}")
        else:
            seen_digits.add(digit)

        if not label:
            errors.append(f"menu option {digit or '?'} label is required")
        if transfer_type not in SUPPORTED_TRANSFER_TYPES:
            errors.append(f"unsupported transfer_type: {transfer_type or '<missing>'}")
        elif transfer_type == "campaign":
            errors.append("campaign transfer is not compiler-supported until a real export proves the XML shape")
        if not target:
            errors.append(f"menu option {digit or '?'} target is required")

        if target and transfer_type == "skill" and target not in required_skills:
            required_skills.append(target)
        if target and transfer_type == "campaign" and target not in required_campaigns:
            required_campaigns.append(target)

    required = {
        "skills": required_skills,
        "campaigns": required_campaigns,
        "prompts": required_prompts,
    }
    return _validation_result(not errors, errors, warnings, required, {}, {})


def compile_simple_menu_ivr(build_plan: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_build_plan(build_plan)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))

    script_name = _clean_string(build_plan["script_name"])
    description = _clean_string(build_plan.get("description"))
    greeting = build_plan["greeting"]
    menu = build_plan["menu"]
    layout = _layout_map(build_plan)

    ids = {
        "incoming": _stable_id(script_name, "incoming"),
        "greeting": _stable_id(script_name, "greeting"),
        "menu": _stable_id(script_name, "menu"),
        "hangup": _stable_id(script_name, "hangup"),
        "hangup_start": _stable_id(script_name, "hangup_start"),
        "hangup_end": _stable_id(script_name, "hangup_end"),
        "prompt": _stable_id(script_name, "prompt"),
    }

    root = ET.Element("ivrScript")
    _add_text(root, "domainId", "0")
    ET.SubElement(root, "properties")
    modules = ET.SubElement(root, "modules")

    incoming_pos = _node_position(layout, "incoming", 40, 180)
    greeting_pos = _node_position(layout, "greeting", 220, 180)
    menu_pos = _node_position(layout, "menu", 420, 180)
    hangup_pos = _node_position(layout, "hangup", 900, 180)

    ivr_blocks.append_incoming_call(
        modules,
        script_name,
        ids["incoming"],
        ids["greeting"],
        _safe_name(script_name),
        incoming_pos[0],
        incoming_pos[1],
    )
    ivr_blocks.append_play(
        modules,
        greeting,
        ids["greeting"],
        ids["incoming"],
        ids["menu"],
        greeting_pos[0],
        greeting_pos[1],
    )

    option_targets: list[dict[str, str]] = []
    for option in menu["options"]:
        option_id = _stable_id(script_name, f"transfer:{option['digit']}:{option['target']}")
        option_targets.append({**option, "module_id": option_id})
    ivr_blocks.append_menu(
        modules,
        menu,
        ids["menu"],
        ids["greeting"],
        ids["hangup"],
        option_targets,
        menu_pos[0],
        menu_pos[1],
    )
    for option in option_targets:
        if option["transfer_type"] == "skill":
            transfer_visual_id = f"transfer_{option['digit']}"
            default_y = 110 + int(option["digit"]) * 70 if option["digit"].isdigit() else 320
            transfer_pos = _node_position(layout, transfer_visual_id, 650, default_y)
            ivr_blocks.append_skill_transfer(
                modules,
                option,
                ids["menu"],
                ids["hangup"],
                transfer_pos[0],
                transfer_pos[1],
            )
        else:
            raise ValueError("campaign transfer is not compiler-supported until a real export proves the XML shape")
    ivr_blocks.append_hangup(
        modules,
        "END_" + _safe_name(script_name),
        ids["hangup"],
        [item["module_id"] for item in option_targets] + [ids["menu"]],
        hangup_pos[0],
        hangup_pos[1],
    )

    ivr_blocks.append_modules_on_hangup(root, ids["hangup_start"], ids["hangup_end"])
    ET.SubElement(root, "userVariables")
    ivr_blocks.append_prompt_catalog(root, greeting, ids["prompt"])
    ivr_blocks.append_empty_language_blocks(root)
    _add_text(root, "defaultLanguage", "en-US")
    _add_text(root, "defaultMethod", "GET")
    _add_text(root, "defaultFetchTimeout", "5")
    _add_text(root, "showLabelNames", "true")
    _add_text(root, "defaultVivrTimeout", "5")
    _add_text(root, "unicodeEncoding", "true")
    _add_text(root, "useShortcut", "false")
    _add_text(root, "resetErrorCode", "false")
    _add_text(root, "showAllChannelPrompts", "false")
    _add_text(root, "extContactFieldsInput", "false")
    _add_text(root, "extContactFieldsOutput", "false")
    _add_text(root, "useIvrTimeZoneInAssignment", "false")
    _add_text(root, "timeoutInMilliseconds", "3600000")
    _add_text(root, "version", "1300001")

    xml_definition = _pretty_xml(root)
    flow_summary = _build_flow_summary(script_name, greeting, menu)
    planned_call = {
        "tool_name": "five9_modify_ivr_script",
        "params": {
            "name": script_name,
            "description": description,
            "xml_definition": xml_definition,
        },
    }
    return {
        "build_plan_schema": BUILD_PLAN_SCHEMA,
        "validation": validation,
        "flow_summary": flow_summary,
        "xmlDefinition": xml_definition,
        "planned_calls": [planned_call],
    }


def validate_canvas_model(canvas: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required: dict[str, list[str]] = {"skills": [], "campaigns": [], "prompts": []}
    metadata: dict[str, Any] = {"uncertified_module_types": [], "locked_module_types": []}

    if not isinstance(canvas, Mapping):
        return _canvas_validation_result(False, ["canvas must be an object"], warnings, required, {}, metadata)
    if canvas.get("view_only") is True or canvas.get("imported_reference") is True:
        errors.append("imported .five9ivr references are view-only; rebuild the script as compiler-backed nodes before compile")

    script_name = _clean_string(canvas.get("script_name"))
    if not script_name:
        errors.append("script_name is required")

    raw_nodes = canvas.get("nodes")
    raw_edges = canvas.get("edges", [])
    if not isinstance(raw_nodes, list) or not raw_nodes:
        errors.append("canvas.nodes must include at least incomingCall and one exit path")
        raw_nodes = []
    if not isinstance(raw_edges, list):
        errors.append("canvas.edges must be a list")
        raw_edges = []

    normalized_nodes: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, node in enumerate(raw_nodes):
        if not isinstance(node, Mapping):
            errors.append(f"node {index + 1} must be an object")
            continue
        node_id = _clean_string(node.get("id")) or f"node_{index + 1}"
        module_type = _clean_string(node.get("module_type"))
        if node_id in seen_ids:
            errors.append(f"duplicate node id: {node_id}")
        seen_ids.add(node_id)
        if not module_type:
            errors.append(f"node {node_id} module_type is required")
            continue
        catalog_entry = MODULE_CATALOG.get(module_type)
        if catalog_entry is None:
            errors.append(f"unknown module type: {module_type}")
            continue
        generation_status = catalog_entry.get("generation_status")
        if generation_status == "unsupported_no_corpus_evidence":
            errors.append(f"{module_type} is locked until a real exported module shape exists")
            metadata["locked_module_types"].append(module_type)
        elif generation_status == "compiler_candidate" and module_type not in metadata["uncertified_module_types"]:
            metadata["uncertified_module_types"].append(module_type)

        config = node.get("config", {})
        if not isinstance(config, Mapping):
            errors.append(f"node {node_id} config must be an object")
            config = {}
        if module_type == "skillTransfer":
            target = _clean_string(config.get("target") or config.get("skill") or node.get("target") or node.get("label"))
            if target and target not in required["skills"]:
                required["skills"].append(target)
        if module_type == "play":
            prompt_name = _clean_string(config.get("prompt_name") or node.get("label"))
            if prompt_name and prompt_name not in required["prompts"]:
                required["prompts"].append(prompt_name)

        position = node.get("position") if isinstance(node.get("position"), Mapping) else {}
        normalized_nodes.append(
            {
                "id": node_id,
                "module_type": module_type,
                "label": _clean_string(node.get("label")) or _module_display_label(module_type),
                "position": {
                    "x": _int_or_default(position.get("x", node.get("x")), 80 + index * 180),
                    "y": _int_or_default(position.get("y", node.get("y")), 120),
                },
                "config": deepcopy(dict(config)),
                "certification": deepcopy(catalog_entry.get("certification", {})),
            }
        )

    node_ids = {node["id"] for node in normalized_nodes}
    normalized_edges: list[dict[str, str]] = []
    for index, edge in enumerate(raw_edges):
        if not isinstance(edge, Mapping):
            errors.append(f"edge {index + 1} must be an object")
            continue
        source = _clean_string(edge.get("source") or edge.get("from"))
        target = _clean_string(edge.get("target") or edge.get("to"))
        label = _clean_string(edge.get("label") or edge.get("branch") or edge.get("output"))
        if source not in node_ids:
            errors.append(f"edge {index + 1} source does not exist: {source or '<missing>'}")
        if target not in node_ids:
            errors.append(f"edge {index + 1} target does not exist: {target or '<missing>'}")
        if source and target and source == target:
            errors.append(f"edge {index + 1} cannot connect a node to itself")
        normalized_edges.append(
            {
                "id": _clean_string(edge.get("id")) or f"edge_{index + 1}",
                "source": source,
                "target": target,
                "label": label,
            }
        )

    module_types = [node["module_type"] for node in normalized_nodes]
    if normalized_nodes and "incomingCall" not in module_types:
        errors.append("canvas must include an incomingCall node")
    if normalized_nodes and "hangup" not in module_types:
        warnings.append("canvas has no hangup node; generated XML may leave caller paths open")
    if normalized_nodes and not normalized_edges:
        errors.append("canvas.edges must include at least one connection")

    if metadata["uncertified_module_types"]:
        warnings.insert(
            0,
            "uncertified module factories present: "
            + ", ".join(sorted(metadata["uncertified_module_types"]))
            + ". Compile is allowed, but live deploy should use certification first.",
        )

    normalized_canvas = {
        "schema": CANVAS_SCHEMA,
        "script_name": script_name,
        "description": _clean_string(canvas.get("description")),
        "nodes": normalized_nodes,
        "edges": normalized_edges,
    }
    return _canvas_validation_result(not errors, errors, warnings, required, normalized_canvas, metadata)


def compile_canvas_ivr(canvas: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_canvas_model(canvas)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))

    normalized = validation["canvas"]
    script_name = normalized["script_name"]
    description = normalized.get("description", "")
    nodes = normalized["nodes"]
    edges = normalized["edges"]
    node_by_id = {node["id"]: node for node in nodes}
    module_ids = {node_id: _stable_id(script_name, f"canvas:{node_id}") for node_id in node_by_id}

    incoming_edges: dict[str, list[dict[str, str]]] = {node_id: [] for node_id in node_by_id}
    outgoing_edges: dict[str, list[dict[str, str]]] = {node_id: [] for node_id in node_by_id}
    for edge in edges:
        mapped = {
            "id": edge["id"],
            "source": module_ids[edge["source"]],
            "target": module_ids[edge["target"]],
            "label": edge.get("label", ""),
            "source_node": edge["source"],
            "target_node": edge["target"],
        }
        outgoing_edges[edge["source"]].append(mapped)
        incoming_edges[edge["target"]].append(mapped)

    root = ET.Element("ivrScript")
    _add_text(root, "domainId", "0")
    ET.SubElement(root, "properties")
    modules = ET.SubElement(root, "modules")

    for node in nodes:
        position = node["position"]
        ivr_blocks.append_canvas_module(
            modules,
            node["module_type"],
            module_ids[node["id"]],
            node["label"],
            node["config"],
            [edge["source"] for edge in incoming_edges[node["id"]]],
            outgoing_edges[node["id"]],
            position["x"],
            position["y"],
        )

    ivr_blocks.append_modules_on_hangup(
        root,
        _stable_id(script_name, "canvas:hangup_start"),
        _stable_id(script_name, "canvas:hangup_end"),
    )
    first_play = next((node for node in nodes if node["module_type"] == "play"), {})
    play_config = first_play.get("config", {}) if isinstance(first_play.get("config"), Mapping) else {}
    ivr_blocks.append_default_root_blocks(
        root,
        prompt_name=_clean_string(play_config.get("prompt_name")) or "Generated Prompt",
        prompt_text=_clean_string(play_config.get("text")),
    )

    xml_definition = _pretty_xml(root)
    deployable = not validation["metadata"].get("uncertified_module_types")
    planned_call = {
        "tool_name": "five9_modify_ivr_script",
        "params": {
            "name": script_name,
            "description": description,
            "xml_definition": xml_definition,
        },
    }
    return {
        "canvas_schema": CANVAS_SCHEMA,
        "validation": validation,
        "flow_summary": _build_canvas_flow_summary(script_name, nodes, edges),
        "xmlDefinition": xml_definition,
        "planned_calls": [planned_call],
        "deployable": deployable,
        "certification_required_modules": sorted(validation["metadata"].get("uncertified_module_types", [])),
    }


def certify_module_factories(
    module_types: list[str] | None = None,
    mode: str = "dry_run",
    approved: bool = False,
    client: Any | None = None,
    target_script_name: str = CERTIFICATION_TARGET_SCRIPT,
) -> dict[str, Any]:
    if mode not in {"dry_run", "live"}:
        raise ValueError("mode must be 'dry_run' or 'live'")
    if mode == "live" and approved is not True:
        raise PermissionError("Live Five9 IVR module certification requires explicit approval")
    if mode == "live" and client is None:
        raise ValueError("client is required for live Five9 IVR module certification")

    selected = module_types or [
        module_type
        for module_type, info in MODULE_CATALOG.items()
        if info.get("generation_status") == "compiler_candidate"
    ]
    results: list[dict[str, Any]] = []
    for module_type in selected:
        status = MODULE_CATALOG.get(module_type, {}).get("generation_status")
        if status == "unsupported_no_corpus_evidence":
            raise ValueError(f"{module_type} is locked until a real exported module shape exists")
        if status not in {"supported_v1", "compiler_candidate"}:
            raise ValueError(f"{module_type} is not a compiler candidate")

        compiled = compile_canvas_ivr(_certification_canvas(target_script_name, module_type))
        timestamp = datetime.now().isoformat(timespec="seconds")
        if mode == "dry_run":
            results.append(
                {
                    "module_type": module_type,
                    "script_name": target_script_name,
                    "timestamp": timestamp,
                    "mode": mode,
                    "result": "planned",
                    "data": {
                        "operation": "modify/readback certification",
                        "xml_length": len(compiled["xmlDefinition"]),
                    },
                }
            )
            continue

        try:
            existing_scripts = client.get_ivr_scripts(name_pattern=f"^{re.escape(target_script_name)}$")
            if not any(
                isinstance(script, Mapping)
                and _clean_string(script.get("name")) == target_script_name
                for script in existing_scripts
            ):
                client.create_ivr_script(name=target_script_name)
            modify_result = client.modify_ivr_script(
                name=target_script_name,
                description=f"Codex module certification: {module_type}",
                xml_definition=compiled["xmlDefinition"],
            )
            readback = client.get_ivr_scripts(name_pattern=target_script_name)
            if not readback:
                raise RuntimeError("readback returned no matching IVR script")
            if not any(
                isinstance(script, Mapping)
                and _clean_string(script.get("xmlDefinition") or script.get("xml_definition"))
                for script in readback
            ):
                raise RuntimeError("readback did not include xmlDefinition for the target IVR script")
            results.append(
                {
                    "module_type": module_type,
                    "script_name": target_script_name,
                    "timestamp": timestamp,
                    "mode": mode,
                    "result": "success",
                    "data": {
                        "modify": modify_result,
                        "readback_count": len(readback),
                    },
                }
            )
        except Exception as exc:
            results.append(
                {
                    "module_type": module_type,
                    "script_name": target_script_name,
                    "timestamp": timestamp,
                    "mode": mode,
                    "result": "failed",
                    "error": str(exc),
                    "data": {},
                }
            )
            break

    return {
        "results": results,
        "summary": {
            "total": len(results),
            "failed": sum(1 for result in results if result.get("result") == "failed"),
            "mode": mode,
            "live": mode == "live",
            "target_script": target_script_name,
        },
    }


def _validation_result(
    valid: bool,
    errors: list[str],
    warnings: list[str],
    required: Mapping[str, Any],
    normalized_plan: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "build_plan_schema": BUILD_PLAN_SCHEMA,
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "required_preflight_objects": deepcopy(dict(required)),
        "normalized_plan": deepcopy(dict(normalized_plan)),
        "metadata": deepcopy(dict(metadata)),
    }


def _visual_canvas_result(
    valid: bool,
    errors: list[str],
    warnings: list[str],
    required: Mapping[str, Any],
    build_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "build_plan_schema": BUILD_PLAN_SCHEMA,
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "required_preflight_objects": deepcopy(dict(required)),
        "build_plan": deepcopy(dict(build_plan or {})),
    }


def _canvas_validation_result(
    valid: bool,
    errors: list[str],
    warnings: list[str],
    required: Mapping[str, Any],
    canvas: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "canvas_schema": CANVAS_SCHEMA,
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "required_preflight_objects": deepcopy(dict(required)),
        "canvas": deepcopy(dict(canvas)),
        "metadata": deepcopy(dict(metadata)),
    }


def _merge_palette_catalog(target: dict[str, dict[str, Any]], source: Mapping[str, Any]) -> None:
    for module_type, info in source.items():
        entry = target.setdefault(
            module_type,
            {
                "module_type": module_type,
                "generation_status": MODULE_CATALOG.get(module_type, {}).get("generation_status", "documented_only"),
                "examples": [],
                "data_fields": [],
                "connection_fields": [],
            },
        )
        for key in ("examples", "data_fields", "connection_fields"):
            entry[key] = sorted(set(entry.get(key, [])) | set(info.get(key, [])))


def _add_module_manual_observation(
    modules: dict[str, dict[str, Any]],
    module: Mapping[str, Any],
    script_name: str,
    edges: list[dict[str, str]],
    branches: list[dict[str, str]],
    transfer_targets: list[dict[str, Any]],
    queries: list[dict[str, str]],
) -> None:
    module_type = _clean_string(module.get("module_type"))
    module_id = _clean_string(module.get("module_id"))
    if not module_type:
        return
    entry = modules.setdefault(
        module_type,
        {
            "module_type": module_type,
            "label": _module_display_label(module_type),
            "group": _module_group(module_type),
            "generation_status": MODULE_CATALOG.get(module_type, {}).get("generation_status", "documented_only"),
            "count": 0,
            "scripts": set(),
            "example_names": [],
            "data_fields": Counter(),
            "connection_fields": Counter(),
            "outgoing_edge_types": Counter(),
            "incoming_count": 0,
            "branch_labels": Counter(),
            "transfer_targets": set(),
            "query_methods": Counter(),
            "query_url_examples": [],
        },
    )
    entry["count"] += 1
    entry["scripts"].add(script_name)
    module_name = _clean_string(module.get("module_name"))
    if module_name and module_name not in entry["example_names"] and len(entry["example_names"]) < 8:
        entry["example_names"].append(module_name)
    entry["data_fields"].update(module.get("data_fields", []))
    entry["connection_fields"].update(module.get("connection_fields", []))
    entry["incoming_count"] += sum(1 for edge in edges if edge.get("to") == module_id)
    entry["outgoing_edge_types"].update(edge.get("type", "") for edge in edges if edge.get("from") == module_id)
    for branch in branches:
        if branch.get("module_id") == module_id and branch.get("label"):
            entry["branch_labels"].update([branch["label"]])
    for target in transfer_targets:
        if target.get("module_id") == module_id:
            entry["transfer_targets"].update(target.get("targets", []))
    for query in queries:
        if query.get("module_id") == module_id:
            entry["query_methods"].update([query.get("method", "")])
            url = query.get("url", "")
            if url and url not in entry["query_url_examples"] and len(entry["query_url_examples"]) < 5:
                entry["query_url_examples"].append(url)


def _finalize_module_manual_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    supported = entry["generation_status"] == "supported_v1"
    data_fields = _counter_to_field_list(entry["data_fields"], entry["count"])
    connection_fields = _counter_to_field_list(entry["connection_fields"], entry["count"])
    outgoing_edges = dict(entry["outgoing_edge_types"].most_common())
    branch_labels = [label for label, _count in entry["branch_labels"].most_common(12) if label]
    instruction = _module_instruction(entry["module_type"], supported, data_fields, connection_fields, outgoing_edges)
    return {
        "module_type": entry["module_type"],
        "label": entry["label"],
        "group": entry["group"],
        "generation_status": entry["generation_status"],
        "compiler_supported": supported,
        "count": entry["count"],
        "script_count": len(entry["scripts"]),
        "example_scripts": sorted(entry["scripts"])[:8],
        "example_names": entry["example_names"],
        "data_fields": data_fields,
        "connection_fields": connection_fields,
        "incoming_count": entry["incoming_count"],
        "outgoing_edge_types": outgoing_edges,
        "branch_labels": branch_labels,
        "transfer_target_examples": sorted(entry["transfer_targets"])[:12],
        "query_methods": dict(entry["query_methods"].most_common()),
        "query_url_examples": entry["query_url_examples"],
        "build_instruction": instruction,
    }


def _counter_to_field_list(counter: Counter, total: int) -> list[dict[str, Any]]:
    fields = []
    for name, count in counter.most_common():
        fields.append(
            {
                "name": name,
                "count": count,
                "presence": "common" if count == total else "optional",
            }
        )
    return fields


def _module_instruction(
    module_type: str,
    supported: bool,
    data_fields: list[dict[str, Any]],
    connection_fields: list[dict[str, Any]],
    outgoing_edges: Mapping[str, int],
) -> dict[str, Any]:
    if supported:
        status = "compiler_ready"
        usage = "AI may request this block through the normalized V1 build plan."
    else:
        status = "reference_only"
        usage = "AI may describe this block in a draft flow, but the V1 compiler must reject deployment until a compiler template exists."
    return {
        "status": status,
        "usage": usage,
        "observed_data_fields": [field["name"] for field in data_fields],
        "observed_connection_fields": [field["name"] for field in connection_fields],
        "observed_outputs": list(outgoing_edges.keys()),
    }


def _build_module_library_summary(entries: list[dict[str, Any]]) -> str:
    lines = ["Five9 IVR Module Building Block Manual", ""]
    for entry in entries:
        status = "compiler-ready" if entry["compiler_supported"] else "reference-only"
        fields = ", ".join(field["name"] for field in entry["data_fields"][:8]) or "no data fields observed"
        outputs = ", ".join(entry["outgoing_edge_types"].keys()) or "no outgoing links observed"
        lines.append(f"- {entry['module_type']} ({status}): {entry['count']} instance(s), fields: {fields}; outputs: {outputs}")
    return "\n".join(lines)


def _visual_palette_entries() -> list[dict[str, Any]]:
    return get_ivr_builder_palette()["modules"]


def _module_display_label(module_type: str) -> str:
    labels = {
        "incomingCall": "Incoming Call",
        "play": "Play",
        "menu": "Menu",
        "skillTransfer": "Skill Transfer",
        "campaignTransfer": "Campaign Transfer",
        "hangup": "Hangup",
        "setVariable": "Set Variable",
        "ifElse": "If / Else",
        "foreignScript": "Foreign Script",
        "thirdPartyTransfer": "Third Party Transfer",
        "voicemailTransfer": "Voicemail Transfer",
    }
    return labels.get(module_type, module_type[:1].upper() + module_type[1:])


def _module_group(module_type: str) -> str:
    groups = {
        "incomingCall": "Entry",
        "startOnHangup": "Entry",
        "play": "Prompt",
        "menu": "Input",
        "input": "Input",
        "getDigits": "Input",
        "skillTransfer": "Transfer",
        "campaignTransfer": "Transfer",
        "agentTransfer": "Transfer",
        "thirdPartyTransfer": "Transfer",
        "extensionTransfer": "Transfer",
        "voiceMailTransfer": "Transfer",
        "voicemailTransfer": "Transfer",
        "ivaTransfer": "Transfer",
        "hangup": "Exit",
        "setVariable": "Logic",
        "case": "Logic",
        "ifElse": "Logic",
        "iterator": "Logic",
        "query": "Integration",
        "foreignScript": "Integration",
        "lookupCRMRecord": "Integration",
        "crmUpdate": "Integration",
        "systemInfo": "System",
        "systemUpdate": "System",
        "setDNC": "System",
        "conference": "Call Control",
        "recording": "Call Control",
        "answerMachine": "Call Control",
        "language": "Prompt",
    }
    return groups.get(module_type, "Other")


def _require_xml_text(xml_definition: str) -> str:
    if xml_definition is None or not str(xml_definition).strip():
        raise ValueError("xml_definition is required")
    return str(xml_definition).strip()


def _clean_string(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _stable_id(script_name: str, key: str) -> str:
    return sha1(f"{script_name}:{key}".encode("utf-8")).hexdigest()[:32].upper()


def _layout_map(build_plan: Mapping[str, Any]) -> Mapping[str, Any]:
    layout = build_plan.get("layout")
    return layout if isinstance(layout, Mapping) else {}


def _node_position(layout: Mapping[str, Any], node_id: str, default_x: int, default_y: int) -> tuple[int, int]:
    raw = layout.get(node_id)
    if not isinstance(raw, Mapping):
        return default_x, default_y
    return _safe_int(raw.get("x"), default_x), _safe_int(raw.get("y"), default_y)


def _int_or_default(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.strip())
    return cleaned.strip("_") or "IVR"


def _add_text(parent: ET.Element, tag: str, value: Any) -> ET.Element:
    child = ET.SubElement(parent, tag)
    child.text = str(value)
    return child


def _summarize_module(module: ET.Element) -> dict[str, Any]:
    data = module.find("data")
    ascendants = [node.text for node in module.findall("ascendants") if node.text]
    single_descendant = module.findtext("singleDescendant") or ""
    exceptional_descendant = module.findtext("exceptionalDescendant") or ""
    connection_fields = []
    if ascendants:
        connection_fields.append("ascendants")
    if single_descendant:
        connection_fields.append("singleDescendant")
    if exceptional_descendant:
        connection_fields.append("exceptionalDescendant")
    if module.findall("./data/branches/entry"):
        connection_fields.append("branches")

    return {
        "module_type": module.tag,
        "module_id": module.findtext("moduleId") or "",
        "module_name": module.findtext("moduleName") or "",
        "ascendants": ascendants,
        "single_descendant": single_descendant,
        "exceptional_descendant": exceptional_descendant,
        "data_fields": [child.tag for child in list(data)] if data is not None else [],
        "connection_fields": connection_fields,
        "connection_status": "connected" if connection_fields else "unconnected",
        "location": {
            "x": module.findtext("locationX") or "",
            "y": module.findtext("locationY") or "",
        },
    }


def _extract_edges(modules: list[ET.Element]) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for module in modules:
        module_id = module.findtext("moduleId") or ""
        single = module.findtext("singleDescendant")
        if module_id and single:
            edges.append({"from": module_id, "to": single, "type": "single"})
        exceptional = module.findtext("exceptionalDescendant")
        if module_id and exceptional:
            edges.append({"from": module_id, "to": exceptional, "type": "exception"})
        for branch in _module_branches(module):
            edges.append(
                {
                    "from": module_id,
                    "to": branch["target_module_id"],
                    "type": "branch",
                    "label": branch["label"],
                }
            )
    return edges


def _extract_branches(modules: list[ET.Element]) -> list[dict[str, str]]:
    branches: list[dict[str, str]] = []
    for module in modules:
        for branch in _module_branches(module):
            branches.append(
                {
                    "module_id": module.findtext("moduleId") or "",
                    "module_name": module.findtext("moduleName") or "",
                    "module_type": module.tag,
                    **branch,
                }
            )
    return branches


def _module_branches(module: ET.Element) -> list[dict[str, str]]:
    branches: list[dict[str, str]] = []
    for entry in module.findall("./data/branches/entry"):
        label = entry.findtext("key") or entry.findtext("value/name") or ""
        target = entry.findtext("value/desc") or ""
        if label and target:
            branches.append({"label": label, "target_module_id": target})
    return branches


def _extract_user_variables(root: ET.Element) -> list[dict[str, str]]:
    variables: list[dict[str, str]] = []
    for entry in root.findall("./userVariables/entry"):
        name = entry.findtext("value/name") or entry.findtext("key") or ""
        if name:
            variables.append(
                {
                    "name": name,
                    "description": entry.findtext("value/description") or "",
                }
            )
    return variables


def _extract_prompts(root: ET.Element) -> list[dict[str, str]]:
    prompts: list[dict[str, str]] = []
    for entry in root.findall("./multiLanguagesPrompts/entry"):
        name = entry.findtext("value/name") or ""
        if name:
            prompts.append(
                {
                    "prompt_id": entry.findtext("value/promptId") or entry.findtext("key") or "",
                    "name": name,
                    "description": entry.findtext("value/description") or "",
                }
            )
    return prompts


def _extract_transfer_targets(modules: list[ET.Element]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for module in modules:
        module_type = module.tag
        if module_type not in {"skillTransfer", "campaignTransfer", "voicemailTransfer", "thirdPartyTransfer"}:
            continue
        names: list[str] = []
        if module_type == "skillTransfer":
            names = _unique_texts(module.findall(".//listOfSkillsEx//extrnalObj/name"))
        elif module_type == "campaignTransfer":
            names = _unique_texts(module.findall(".//campaign/name") + module.findall(".//listOfCampaignsEx//extrnalObj/name"))
        else:
            names = _unique_texts(module.findall(".//name"))
        targets.append(
            {
                "module_id": module.findtext("moduleId") or "",
                "module_type": module_type,
                "targets": names,
            }
        )
    return targets


def _extract_queries(modules: list[ET.Element]) -> list[dict[str, str]]:
    queries: list[dict[str, str]] = []
    for module in modules:
        if module.tag != "query":
            continue
        queries.append(
            {
                "module_id": module.findtext("moduleId") or "",
                "module_name": module.findtext("moduleName") or "",
                "url": module.findtext("./data/url") or "",
                "method": module.findtext("./data/method") or "",
            }
        )
    return queries


def _unique_texts(nodes: list[ET.Element]) -> list[str]:
    values: list[str] = []
    for node in nodes:
        value = _clean_string(node.text)
        if value and value not in values:
            values.append(value)
    return values


def _append_incoming_call(modules: ET.Element, script_name: str, module_id: str, next_id: str) -> None:
    module = ET.SubElement(modules, "incomingCall")
    _add_text(module, "singleDescendant", next_id)
    _add_text(module, "moduleName", "START_" + _safe_name(script_name))
    _add_text(module, "locationX", "40")
    _add_text(module, "locationY", "180")
    _add_text(module, "moduleId", module_id)
    ET.SubElement(module, "data")


def _append_play(modules: ET.Element, greeting: Mapping[str, Any], module_id: str, ascendant: str, next_id: str) -> None:
    module = ET.SubElement(modules, "play")
    _add_text(module, "ascendants", ascendant)
    _add_text(module, "singleDescendant", next_id)
    _add_text(module, "moduleName", "Greeting")
    _add_text(module, "locationX", "220")
    _add_text(module, "locationY", "180")
    _add_text(module, "moduleId", module_id)
    data = ET.SubElement(module, "data")
    prompt = ET.SubElement(data, "prompt")
    _add_text(prompt, "name", _clean_string(greeting.get("prompt_name")))
    _add_text(prompt, "text", _clean_string(greeting.get("text")))


def _append_menu(
    modules: ET.Element,
    menu: Mapping[str, Any],
    module_id: str,
    ascendant: str,
    hangup_id: str,
    option_targets: list[dict[str, str]],
) -> None:
    module = ET.SubElement(modules, "menu")
    _add_text(module, "ascendants", ascendant)
    _add_text(module, "moduleName", _clean_string(menu.get("name")))
    _add_text(module, "locationX", "420")
    _add_text(module, "locationY", "180")
    _add_text(module, "moduleId", module_id)
    data = ET.SubElement(module, "data")
    branches = ET.SubElement(data, "branches")
    for option in option_targets:
        _append_branch(branches, option["digit"], option["label"], option["module_id"])
    _append_branch(branches, "No Match", "No Match", hangup_id)
    _append_branch(branches, "No Input", "No Input", hangup_id)


def _append_branch(parent: ET.Element, key: str, name: str, target_id: str) -> None:
    entry = ET.SubElement(parent, "entry")
    _add_text(entry, "key", key)
    value = ET.SubElement(entry, "value")
    _add_text(value, "name", name)
    _add_text(value, "desc", target_id)


def _append_skill_transfer(modules: ET.Element, option: Mapping[str, str], ascendant: str, hangup_id: str) -> None:
    module = ET.SubElement(modules, "skillTransfer")
    _add_text(module, "ascendants", ascendant)
    _add_text(module, "singleDescendant", hangup_id)
    _add_text(module, "moduleName", f"TransferTo{_safe_name(option['label'])}")
    _add_text(module, "locationX", "650")
    _add_text(module, "locationY", str(110 + int(option["digit"]) * 70 if option["digit"].isdigit() else 320))
    _add_text(module, "moduleId", option["module_id"])
    data = ET.SubElement(module, "data")
    skills = ET.SubElement(data, "listOfSkillsEx")
    skill = ET.SubElement(skills, "extrnalObj")
    _add_text(skill, "id", "0")
    _add_text(skill, "name", option["target"])
    _add_text(skills, "varSelected", "false")


def _append_campaign_transfer(modules: ET.Element, option: Mapping[str, str], ascendant: str, hangup_id: str) -> None:
    module = ET.SubElement(modules, "campaignTransfer")
    _add_text(module, "ascendants", ascendant)
    _add_text(module, "singleDescendant", hangup_id)
    _add_text(module, "moduleName", f"TransferTo{_safe_name(option['label'])}")
    _add_text(module, "locationX", "650")
    _add_text(module, "locationY", str(110 + int(option["digit"]) * 70 if option["digit"].isdigit() else 320))
    _add_text(module, "moduleId", option["module_id"])
    data = ET.SubElement(module, "data")
    campaign = ET.SubElement(data, "campaign")
    _add_text(campaign, "name", option["target"])


def _append_hangup(modules: ET.Element, module_name: str, module_id: str, ascendants: list[str]) -> None:
    module = ET.SubElement(modules, "hangup")
    for ascendant in ascendants:
        _add_text(module, "ascendants", ascendant)
    _add_text(module, "moduleName", module_name)
    _add_text(module, "locationX", "900")
    _add_text(module, "locationY", "180")
    _add_text(module, "moduleId", module_id)
    data = ET.SubElement(module, "data")
    dispo = ET.SubElement(data, "dispo")
    _add_text(dispo, "id", "0")
    _add_text(dispo, "name", "No Disposition")
    _add_text(data, "returnToCallingModule", "true")
    _add_text(data, "overwriteDisposition", "true")


def _append_modules_on_hangup(root: ET.Element, start_id: str, hangup_id: str) -> None:
    modules = ET.SubElement(root, "modulesOnHangup")
    start = ET.SubElement(modules, "startOnHangup")
    _add_text(start, "singleDescendant", hangup_id)
    _add_text(start, "moduleName", "StartOnHangup1")
    _add_text(start, "locationX", "20")
    _add_text(start, "locationY", "10")
    _add_text(start, "moduleId", start_id)
    hangup = ET.SubElement(modules, "hangup")
    _add_text(hangup, "ascendants", start_id)
    _add_text(hangup, "moduleName", "Hangup1")
    _add_text(hangup, "locationX", "120")
    _add_text(hangup, "locationY", "10")
    _add_text(hangup, "moduleId", hangup_id)
    data = ET.SubElement(hangup, "data")
    dispo = ET.SubElement(data, "dispo")
    _add_text(dispo, "id", "-17")
    _add_text(dispo, "name", "Caller Disconnected")
    _add_text(data, "returnToCallingModule", "true")
    _add_text(data, "overwriteDisposition", "false")


def _append_prompt_catalog(root: ET.Element, greeting: Mapping[str, Any], prompt_id: str) -> None:
    prompts = ET.SubElement(root, "multiLanguagesPrompts")
    entry = ET.SubElement(prompts, "entry")
    _add_text(entry, "key", prompt_id)
    value = ET.SubElement(entry, "value")
    _add_text(value, "promptId", prompt_id)
    _add_text(value, "name", _clean_string(greeting.get("prompt_name")))
    _add_text(value, "description", _clean_string(greeting.get("text")))
    _add_text(value, "type", "AUDIO")
    _add_text(value, "defaultLanguage", "en-US")
    _add_text(value, "isPersistent", "true")


def _append_empty_language_blocks(root: ET.Element) -> None:
    for tag in (
        "multiLanguagesVIVRPrompts",
        "multiLanguagesTextPrompts",
        "multiLanguagesMenuChoices",
        "multiLanguagesEwtAnnouncement",
        "languages",
        "functions",
    ):
        ET.SubElement(root, tag)


def _build_flow_summary(script_name: str, greeting: Mapping[str, Any], menu: Mapping[str, Any]) -> str:
    lines = [
        f"Script: {script_name}",
        f"Incoming Call -> Greeting prompt '{_clean_string(greeting.get('prompt_name'))}' -> {menu['name']}",
    ]
    for option in menu["options"]:
        lines.append(
            f"{menu['name']} option {option['digit']} ({option['label']}) -> {option['transfer_type']} transfer: {option['target']}"
        )
    lines.append(f"{menu['name']} No Match / No Input -> Hangup")
    return "\n".join(lines)


def _build_canvas_flow_summary(script_name: str, nodes: list[Mapping[str, Any]], edges: list[Mapping[str, str]]) -> str:
    label_by_id = {node["id"]: f"{node['label']} ({node['module_type']})" for node in nodes}
    lines = [f"Script: {script_name}", f"Canvas nodes: {len(nodes)}", f"Canvas edges: {len(edges)}"]
    for edge in edges:
        label = f" [{edge['label']}]" if edge.get("label") else ""
        lines.append(f"{label_by_id.get(edge['source'], edge['source'])}{label} -> {label_by_id.get(edge['target'], edge['target'])}")
    return "\n".join(lines)


def _certification_canvas(script_name: str, module_type: str) -> dict[str, Any]:
    middle_id = f"candidate_{module_type}"
    config = _default_canvas_config(module_type)
    return {
        "schema": CANVAS_SCHEMA,
        "script_name": script_name,
        "description": f"Codex module certification: {module_type}",
        "nodes": [
            {"id": "incoming", "module_type": "incomingCall", "label": "Incoming Call", "position": {"x": 40, "y": 120}},
            {
                "id": middle_id,
                "module_type": module_type,
                "label": _module_display_label(module_type),
                "position": {"x": 260, "y": 120},
                "config": config,
            },
            {"id": "hangup", "module_type": "hangup", "label": "Hangup", "position": {"x": 520, "y": 120}},
        ],
        "edges": [
            {"id": "edge_incoming_candidate", "source": "incoming", "target": middle_id, "label": ""},
            {"id": "edge_candidate_hangup", "source": middle_id, "target": "hangup", "label": "success"},
        ],
    }


def _default_canvas_config(module_type: str) -> dict[str, Any]:
    defaults: dict[str, dict[str, Any]] = {
        "play": {"prompt_name": "Certification Greeting", "text": "Certification test."},
        "menu": {"useDTMF": "true"},
        "skillTransfer": {"target": "ZZ_TEST_Codex_Skill"},
        "getDigits": {"targetVariableName": "digits", "numberOfDigits": 1},
        "setVariable": {"variableName": "codexVar", "value": "test"},
        "query": {"url": "https://example.com/five9-certification", "method": "GET"},
        "foreignScript": {"ivrScript": "ZZ_TEST_Codex_IVR_Source"},
        "voiceMailTransfer": {"target": "ZZ_TEST_Codex_Skill"},
        "thirdPartyTransfer": {"target": "15555550100", "destination": "15555550100"},
        "agentTransfer": {"target": "ZZ_TEST_Codex_Agent"},
        "extensionTransfer": {"target": "1000", "destination": "1000"},
        "ivaTransfer": {"target": "ZZ_TEST_Codex_IVA"},
        "language": {"language": "en-US"},
        "input": {"targetVariableName": "input"},
        "recording": {"varToAccessRecording": "recordingUrl"},
        "iterator": {"collection": "items"},
        "lookupCRMRecord": {"lookupCriteria": "ANI"},
        "crmUpdate": {"mode": "UPDATE"},
        "systemInfo": {"systemInfoType": "CALL"},
        "systemUpdate": {"objectToModify": "CALL"},
        "setDNC": {"targetVariableName": "ani"},
        "conference": {"destination": "15555550100"},
        "ifElse": {"condition": "true"},
        "case": {"condition": "default"},
        "answerMachine": {"condition": "live"},
    }
    return deepcopy(defaults.get(module_type, {}))


def _pretty_xml(root: ET.Element) -> str:
    rough = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(rough)
    pretty = parsed.toprettyxml(indent="    ", encoding="UTF-8").decode("utf-8")
    return "\n".join(line for line in pretty.splitlines() if line.strip())


__all__ = [
    "BUILD_PLAN_SCHEMA",
    "DEFAULT_ALL_MODULES_EXPORT",
    "DEFAULT_IVR_EXPORT_FOLDER",
    "SAMPLE_BUILD_PLAN",
    "analyze_module_palette",
    "analyze_module_palette_file",
    "analyze_module_library",
    "analyze_ivr_export_folder",
    "analyze_ivr_file",
    "certify_module_factories",
    "compile_canvas_ivr",
    "compile_simple_menu_ivr",
    "get_ivr_builder_catalog",
    "get_ivr_builder_palette",
    "parse_ivr_xml",
    "validate_build_plan",
    "validate_canvas_model",
    "validate_visual_canvas",
    "visual_canvas_to_build_plan",
    "visualize_build_plan",
]
