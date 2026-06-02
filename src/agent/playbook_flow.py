from __future__ import annotations

from ast import literal_eval
import re
from pathlib import Path
from typing import Any, Iterable, Mapping
from xml.etree import ElementTree as ET
from zipfile import ZipFile


SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"m": SPREADSHEET_NS, "r": REL_NS}

SUPPORTED_EXTENSION = ".xlsx"
DEFERRED_ITEMS = [
    "IVR XML generation deferred; playbook intake may create the IVR script shell but does not generate or upload raw script XML.",
]


def analyze_playbook(playbook_path: str | Path) -> dict[str, Any]:
    path = _validate_playbook_path(playbook_path)
    workbook = read_xlsx_workbook(path)
    entities = extract_five9_entities(workbook)
    ivr_requirements = extract_ivr_requirements(entities, workbook)
    preflight_plan = build_preflight_plan(entities)
    core_write_plan = build_core_write_plan(
        entities,
        default_ivr_script_name=ivr_requirements.get("script_name"),
    )

    return {
        "source": {
            "file_name": path.name,
            "path": str(path),
            "sheets": list(workbook.keys()),
        },
        "requirements": build_requirement_groups(entities),
        "entities": entities,
        "ivr_requirements": ivr_requirements,
        "preflight_plan": preflight_plan,
        "core_write_plan": core_write_plan,
        "deferred": list(DEFERRED_ITEMS),
        "summary": {
            "skills": len(entities["skills"]),
            "dispositions": len(entities["dispositions"]),
            "prompts": len(entities["prompts"]),
            "inbound_campaigns": len(entities["inbound_campaigns"]),
            "dnis": len(entities["dnis"]),
            "ivr_requirements": 1 if _ivr_has_content(ivr_requirements) else 0,
            "preflight_calls": len(preflight_plan),
            "core_write_calls": len(core_write_plan),
            "includes_ivr_scripts": False,
        },
    }


def read_xlsx_workbook(path: str | Path) -> dict[str, list[list[str]]]:
    workbook_path = Path(path)
    with ZipFile(workbook_path) as archive:
        shared_strings = _read_shared_strings(archive)
        workbook_xml = ET.fromstring(archive.read("xl/workbook.xml"))
        rels_xml = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_targets = {
            rel.attrib["Id"]: _normalize_target(rel.attrib["Target"])
            for rel in rels_xml
        }

        sheets: dict[str, list[list[str]]] = {}
        sheets_node = workbook_xml.find("m:sheets", NS)
        for sheet in list(sheets_node) if sheets_node is not None else []:
            name = sheet.attrib["name"]
            rel_id = sheet.attrib[f"{{{REL_NS}}}id"]
            target = rel_targets[rel_id]
            sheets[name] = _read_sheet_rows(archive, target, shared_strings)
        return sheets


def extract_five9_entities(workbook: dict[str, list[list[str]]]) -> dict[str, Any]:
    skills = _extract_skills(workbook.get("Skill", []))
    dispositions = _extract_dispositions(workbook.get("Dispositions", []))
    prompts = _extract_prompts(workbook.get("Prompts", []))
    inbound_campaigns = _extract_inbound_campaigns(workbook.get("Inbound", []))
    dnis = _extract_dnis(workbook)

    return {
        "skills": skills,
        "dispositions": dispositions,
        "prompts": prompts,
        "inbound_campaigns": inbound_campaigns,
        "dnis": dnis,
    }


def extract_ivr_requirements(
    entities: dict[str, Any],
    workbook: dict[str, list[list[str]]] | None = None,
) -> dict[str, Any]:
    route_names = _unique(
        [
            entry.get("route_to", "")
            for entry in entities.get("dnis", [])
            if entry.get("route_to")
        ]
    )
    campaign_names = [campaign["campaign_name"] for campaign in entities.get("inbound_campaigns", [])]
    prompt_names = [prompt["prompt_name"] for prompt in entities.get("prompts", [])]
    script_name = _first_likely_ivr_name(route_names) or _first_likely_ivr_name(campaign_names)
    routing_targets = _unique(route_names + campaign_names)
    menu_options = [
        {"digit": str(index), "label": target, "target": target}
        for index, target in enumerate(routing_targets[:9], start=1)
    ]
    notes = list(DEFERRED_ITEMS)
    if route_names:
        notes.append("Workbook contains DNIS routing destinations that should inform IVR script design.")
    if campaign_names:
        notes.append("Inbound campaign names are available as potential transfer targets.")
    return {
        "script_name": script_name,
        "intent": "Capture IVR routing intent from workbook; XML generation is deferred.",
        "business_hours": _extract_business_hours_note(workbook or {}),
        "greetings": prompt_names,
        "menu_options": menu_options,
        "routing_targets": routing_targets,
        "notes": _unique(notes),
    }


def build_requirement_groups(entities: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "Skills": [f"Create or verify skill: {name}" for name in entities["skills"]],
        "Dispositions": [
            f"Create or verify disposition: {name}"
            for name in entities["dispositions"]
        ],
        "Prompts": [
            f"Create or verify prompt: {prompt['prompt_name']}"
            for prompt in entities["prompts"]
        ],
        "Inbound Campaigns": [
            f"Create or verify inbound campaign: {campaign['campaign_name']}"
            for campaign in entities["inbound_campaigns"]
        ],
        "DNIS / Routing": [
            f"Route DNIS {entry['number']} to {entry.get('campaign_name') or entry.get('route_to') or 'review'}"
            for entry in entities["dnis"]
        ],
        "Deferred": list(DEFERRED_ITEMS),
    }


def _ivr_has_content(ivr_requirements: dict[str, Any]) -> bool:
    return any(
        ivr_requirements.get(key)
        for key in ("script_name", "intent", "business_hours", "greetings", "menu_options", "routing_targets", "notes")
    )


def _first_likely_ivr_name(values: list[str]) -> str:
    for value in values:
        lowered = value.lower()
        if "ivr" in lowered or "main" in lowered or "inbound" in lowered:
            return value
    return values[0] if values else ""


def _extract_business_hours_note(workbook: dict[str, list[list[str]]]) -> str:
    for sheet_name in ("Config Summary", "Instructions", "Inbound"):
        for row in workbook.get(sheet_name, []):
            joined = " ".join(cell for cell in row if cell).strip()
            lowered = joined.lower()
            if "business hour" in lowered or "hours of operation" in lowered:
                return joined
    return ""


def build_preflight_plan(entities: dict[str, Any]) -> list[dict[str, Any]]:
    plan = [
        {"tool_name": "five9_get_skills", "params": {}},
        {"tool_name": "five9_get_dispositions", "params": {}},
        {"tool_name": "five9_get_prompts", "params": {}},
        {"tool_name": "five9_get_campaigns", "params": {"campaign_type": "inbound"}},
        {"tool_name": "five9_get_dnis_list", "params": {}},
    ]
    for campaign in entities.get("inbound_campaigns", []):
        plan.append(
            {
                "tool_name": "five9_get_campaign_dnis_list",
                "params": {"campaign_name": campaign["campaign_name"]},
            }
        )
    return plan


def build_core_write_plan(
    entities: dict[str, Any],
    default_ivr_script_name: str | None = None,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    for raw_skill in entities["skills"]:
        skill = _clean_playbook_name(raw_skill)
        calls.append(
            {
                "tool_name": "five9_create_skill",
                "params": {
                    "name": skill,
                    "description": f"Skill imported from implementation playbook: {skill}",
                },
            }
        )

    for raw_disposition in entities["dispositions"]:
        disposition = _clean_playbook_name(raw_disposition)
        calls.append(
            {
                "tool_name": "five9_create_disposition",
                "params": {"name": disposition},
            }
        )

    for prompt in entities["prompts"]:
        calls.append({"tool_name": "five9_add_prompt_tts", "params": dict(prompt)})

    for campaign in entities["inbound_campaigns"]:
        campaign_name = campaign["campaign_name"]
        script_name = (
            campaign.get("default_ivr_script_name")
            or default_ivr_script_name
        )
        if not script_name:
            raise ValueError(
                f"default_ivr_script_name is required to create inbound campaign: {campaign_name}"
            )
        calls.append(
            {
                "tool_name": "five9_create_inbound_campaign",
                "params": {
                    "campaign_name": campaign_name,
                    "default_ivr_script_name": script_name,
                    "description": campaign.get("description"),
                },
            }
        )
        if campaign.get("skills"):
            calls.append(
                {
                    "tool_name": "five9_add_skills_to_campaign",
                    "params": {
                        "campaign_name": campaign_name,
                        "skills": campaign["skills"],
                    },
                }
            )
        if campaign.get("dispositions"):
            calls.append(
                {
                    "tool_name": "five9_add_dispositions_to_campaign",
                    "params": {
                        "campaign_name": campaign_name,
                        "dispositions": campaign["dispositions"],
                    },
                }
            )

    for entry in entities["dnis"]:
        campaign_name = entry.get("campaign_name")
        if campaign_name:
            calls.append(
                {
                    "tool_name": "five9_add_dnis_to_campaign",
                    "params": {
                        "campaign_name": campaign_name,
                        "dnis": [entry["number"]],
                    },
                }
            )

    return calls


def _validate_playbook_path(playbook_path: str | Path) -> Path:
    if not playbook_path or not str(playbook_path).strip():
        raise ValueError("playbook_path is required")
    path = Path(playbook_path)
    if not path.exists():
        raise FileNotFoundError(f"Playbook not found: {path}")
    if path.suffix.lower() != SUPPORTED_EXTENSION:
        raise ValueError("Only .xlsx playbooks are supported in this first agent slice")
    return path


def _read_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(text.text or "" for text in item.iter(f"{{{SPREADSHEET_NS}}}t"))
        for item in root.findall("m:si", NS)
    ]


def _normalize_target(target: str) -> str:
    target = target.lstrip("/")
    if target.startswith("xl/"):
        return target
    return f"xl/{target}"


def _read_sheet_rows(
    archive: ZipFile,
    target: str,
    shared_strings: list[str],
) -> list[list[str]]:
    root = ET.fromstring(archive.read(target))
    rows: list[list[str]] = []
    for row in root.findall(".//m:sheetData/m:row", NS):
        values_by_col: dict[int, str] = {}
        for cell in row.findall("m:c", NS):
            cell_ref = cell.attrib.get("r", "")
            col_index = _column_index(cell_ref)
            values_by_col[col_index] = _cell_value(cell, shared_strings).strip()
        if not values_by_col:
            continue
        max_col = max(values_by_col)
        values = [values_by_col.get(index, "") for index in range(max_col + 1)]
        if any(values):
            rows.append(values)
    return rows


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.iter(f"{{{SPREADSHEET_NS}}}t"))

    value = cell.find("m:v", NS)
    if value is None or value.text is None:
        return ""
    if cell_type == "s":
        return shared_strings[int(value.text)]
    return value.text


def _column_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        return 0
    index = 0
    for char in match.group(1):
        index = index * 26 + ord(char) - 64
    return index - 1


def _extract_skills(rows: list[list[str]]) -> list[str]:
    values = []
    header_index = _find_header_index(rows, {"skill name"})
    if header_index < 0:
        header_index = _find_header_index(rows, {"name"})
    headers = _normalized_headers(rows[header_index]) if header_index >= 0 else {}
    name_col = headers.get("skill name", headers.get("name", 0))
    for row in rows[header_index + 1:]:
        name = _clean_playbook_name(_cell(row, name_col))
        if name.lower().endswith("matrix"):
            break
        if _is_data_name(name):
            values.append(name)
    return _unique(values)


def _extract_dispositions(rows: list[list[str]]) -> list[str]:
    header_index = _find_header_index(rows, {"disposition name"})
    headers = _normalized_headers(rows[header_index]) if header_index >= 0 else {}
    name_col = headers.get("disposition name", 1)
    notes_col = headers.get("notes")
    values = []
    for row in rows[header_index + 1:]:
        name = _clean_playbook_name(_cell(row, name_col))
        notes = _cell(row, notes_col) if notes_col is not None else ""
        if "system dispo" in notes.lower():
            continue
        if _is_data_name(name):
            values.append(name)
    return _unique(values)


def _extract_prompts(rows: list[list[str]]) -> list[dict[str, str]]:
    header_index = _find_header_index(rows, {"prompt name", "prompt script verbiage"})
    if header_index < 0:
        header_index = _find_header_index(rows, {"name", "prompt script verbiage"})
    headers = _normalized_headers(rows[header_index]) if header_index >= 0 else {}
    name_col = headers.get("prompt name", headers.get("name", 0))
    text_col = headers.get("prompt script verbiage")
    status_col = headers.get("prompt status")
    prompts = []
    for row in rows[header_index + 1:]:
        name = _cell(row, name_col)
        text = _cell(row, text_col) if text_col is not None else ""
        status = _cell(row, status_col).lower() if status_col is not None else ""
        if not _is_data_name(name) or status == "ignore":
            continue
        if text:
            prompts.append({"prompt_name": name, "text": text})
    return prompts


def _extract_inbound_campaigns(rows: list[list[str]]) -> list[dict[str, Any]]:
    header_index = _find_header_index(rows, {"campaign name", "inbound skill"})
    if header_index < 0:
        header_index = _find_header_index(rows, {"name", "inbound skill"})
    headers = _normalized_headers(rows[header_index]) if header_index >= 0 else {}
    name_col = headers.get("campaign name", headers.get("name", 0))
    campaigns = []
    for row in rows[header_index + 1:]:
        name = _cell(row, name_col)
        if not _is_data_name(name):
            continue
        skills = _split_names(_cell(row, headers.get("inbound skill")))
        dispositions = _split_names(_cell(row, headers.get("dispositions")))
        if dispositions == ["All"]:
            dispositions = []
        campaigns.append(
            {
                "campaign_name": name,
                "skills": skills,
                "dispositions": dispositions,
                "description": _cell(row, headers.get("description")),
                "campaign_profile": _cell(row, headers.get("campaign profile")),
            }
        )
    return campaigns


def _extract_dnis(workbook: dict[str, list[list[str]]]) -> list[dict[str, str]]:
    entries = []
    entries.extend(_extract_number_rows(workbook.get("Number Inventory", []), "number", "assigned campaign", "assigned ivr / routing destination"))
    entries.extend(_extract_number_rows(workbook.get("DID.Tracker", []), "name", "five9 campaign", "description"))
    return _dedupe_dicts(entries, "number", "campaign_name", "route_to")


def _extract_number_rows(
    rows: list[list[str]],
    number_header: str,
    campaign_header: str,
    route_header: str,
) -> list[dict[str, str]]:
    entries = []
    for header_index in _all_header_indexes(rows, {number_header}):
        headers = _normalized_headers(rows[header_index])
        number_col = headers.get(number_header)
        campaign_col = headers.get(campaign_header)
        route_col = headers.get(route_header)
        for row in rows[header_index + 1:]:
            number = _cell(row, number_col)
            if not _looks_like_number(number):
                if _looks_like_section_break(number):
                    break
                continue
            entry = {"number": number}
            campaign = _cell(row, campaign_col)
            route_to = _cell(row, route_col)
            if campaign:
                entry["campaign_name"] = campaign
            if route_to:
                entry["route_to"] = route_to
            entries.append(entry)
    return entries


def _find_header_index(rows: list[list[str]], required_headers: set[str]) -> int:
    for index, row in enumerate(rows):
        headers = set(_normalized_headers(row))
        if required_headers.issubset(headers):
            return index
    return -1


def _all_header_indexes(rows: list[list[str]], required_headers: set[str]) -> list[int]:
    return [
        index
        for index, row in enumerate(rows)
        if required_headers.issubset(set(_normalized_headers(row)))
    ]


def _normalized_headers(row: list[str]) -> dict[str, int]:
    return {
        _normalize_header(value): index
        for index, value in enumerate(row)
        if _normalize_header(value)
    }


def _normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _first_cell(row: list[str]) -> str:
    for value in row:
        if value:
            return value.strip()
    return ""


def _cell(row: list[str], index: int | None) -> str:
    if index is None or index < 0 or index >= len(row):
        return ""
    return str(row[index] or "").strip()


def _is_data_name(value: str) -> bool:
    if not value or len(value.strip()) < 2:
        return False
    lowered = value.strip().lower()
    return lowered not in {"name", "group 1", "five9 skills", "five9 dispositions", "five9 prompts"}


def _split_names(value: str) -> list[str]:
    if not value:
        return []
    structured_name = _structured_name_from_cell(value)
    if structured_name:
        return [structured_name]
    parts = re.split(r"[,;\n]+", value)
    return _unique(_clean_playbook_name(part) for part in parts if part.strip())


def _clean_playbook_name(value: str) -> str:
    structured_name = _structured_name_from_cell(value)
    if structured_name:
        return structured_name
    return str(value or "").strip()


def _structured_name_from_cell(value: str) -> str:
    text = str(value or "").strip()
    if not (text.startswith("{") and text.endswith("}")):
        return ""
    try:
        parsed = literal_eval(text)
    except (SyntaxError, ValueError):
        return ""
    if not isinstance(parsed, Mapping):
        return ""
    name = str(parsed.get("name") or "").strip()
    return name


def _looks_like_number(value: str) -> bool:
    if not value:
        return False
    return bool(re.search(r"\d{6,}", value))


def _looks_like_section_break(value: str) -> bool:
    return value.strip().lower() in {"did", "tfn", "number", "name"}


def _unique(values: Iterable[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        clean = str(value).strip()
        if clean and clean not in seen:
            seen.add(clean)
            output.append(clean)
    return output


def _dedupe_dicts(items: list[dict[str, str]], *keys: str) -> list[dict[str, str]]:
    seen = set()
    output = []
    for item in items:
        identity = tuple(item.get(key, "") for key in keys)
        if identity in seen:
            continue
        seen.add(identity)
        output.append(item)
    return output


__all__ = [
    "analyze_playbook",
    "build_core_write_plan",
    "build_preflight_plan",
    "extract_five9_entities",
    "extract_ivr_requirements",
    "read_xlsx_workbook",
]
