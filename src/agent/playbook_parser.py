from __future__ import annotations

from pathlib import Path
from typing import Any

from .playbook_flow import (
    analyze_playbook,
    build_requirement_groups,
    extract_five9_entities,
    extract_ivr_requirements,
    read_xlsx_workbook,
)


def parse_playbook(playbook_path: str | Path) -> dict[str, Any]:
    return analyze_playbook(playbook_path)


def parse_uploaded_playbook(filename: str, data: bytes, temp_dir: str | Path) -> dict[str, Any]:
    if not filename.lower().endswith(".xlsx"):
        raise ValueError("Only .xlsx playbooks are supported")
    target = Path(temp_dir) / filename
    target.write_bytes(data)
    return parse_playbook(target)


__all__ = [
    "build_requirement_groups",
    "extract_five9_entities",
    "extract_ivr_requirements",
    "parse_playbook",
    "parse_uploaded_playbook",
    "read_xlsx_workbook",
]
