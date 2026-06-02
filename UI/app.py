"""
app.py - CCaaS Automation Tools UI Backend

Run with:
    cd UI
    pip install -r requirements.txt
    python app.py

Then open http://127.0.0.1:8000
"""

import sys
import os
import subprocess
import tempfile
import textwrap
import traceback
from pathlib import Path
from fastapi import FastAPI, Form, HTTPException, Query
from fastapi import File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import uvicorn
from dotenv import load_dotenv

# Allow importing tool modules from sibling directories
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.demo_flow import (
    STUB_EXECUTION_MESSAGE,
    analyze_requirements,
    execute_stub_plan,
)
from src.agent.playbook_flow import analyze_playbook
from src.agent.graph import run_playbook_agent
from src.agent.planner import plans_match
from src.agent.schemas import (
    ALLOWED_CORE_WRITE_TOOL_NAMES,
    validate_agent_executable_plan,
    validate_ivr_script_plan,
    validate_planned_calls,
)
from src.tools.Five9.preflight_pack import dispatcher as five9_preflight
from src.tools.Five9.core_config import dispatcher as five9_core_writes
from src.tools.Five9.modify_config import dispatcher as five9_modify
from src.tools.Five9.rollback_pack import dispatcher as five9_rollback
from src.tools.Five9.ivr.scripts import dispatcher as five9_ivr_scripts
from src.tools.Five9.ivr.builder import facade as five9_ivr_builder
from src.tools.Five9.common.soap_client import Five9ConfigClient

TOOL_PATHS = {
    "five9.prompt_bulk_upload": ROOT / "src" / "tools" / "Five9" / "Prompt_Management" / "Prompt_Bulk_Upload",
}

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="CCaaS Automation Tools")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

AGENT_PLAN_STORE: dict[str, list[dict[str, Any]]] = {}


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/demo")
def demo():
    return FileResponse(str(STATIC_DIR / "demo.html"))


# ---------------------------------------------------------------------------
# Native file/folder picker
# Launched as a detached process so it gets its own desktop session and
# the dialog actually appears. Result is written to a temp file.
# ---------------------------------------------------------------------------

FILTER_MAP = {
    "csv": [("CSV files", "*.csv"), ("All files", "*.*")],
    "wav": [("WAV files", "*.wav"), ("All files", "*.*")],
    "xlsx": [("Excel workbooks", "*.xlsx"), ("All files", "*.*")],
    "five9ivr": [("Five9 IVR scripts", "*.five9ivr"), ("XML files", "*.xml"), ("All files", "*.*")],
    "all": [("All files", "*.*")],
}

_PICKER_PY = textwrap.dedent("""
    import sys, tkinter as tk
    from tkinter import filedialog
    mode, title, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    filters = eval(sys.argv[4]) if len(sys.argv) > 4 else [("All files", "*.*")]
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.lift()
    if mode == "file":
        path = filedialog.askopenfilename(title=title, filetypes=filters, parent=root)
    else:
        path = filedialog.askdirectory(title=title, parent=root)
    root.destroy()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(path or "")
""")


def _run_picker(mode: str, title: str, filters=None) -> str:
    filters = filters or [("All files", "*.*")]

    fd, py_path = tempfile.mkstemp(suffix=".py")
    fd2, out_path = tempfile.mkstemp(suffix=".txt")
    os.close(fd2)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(_PICKER_PY)

        # CREATE_NEW_CONSOLE keeps the subprocess on the interactive desktop
        # (required for GUI dialogs). SW_HIDE suppresses the console window flash.
        si = subprocess.STARTUPINFO()
        si.dwFlags = subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE

        proc = subprocess.Popen(
            [sys.executable, py_path, mode, title, out_path, repr(filters)],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            startupinfo=si,
            close_fds=True,
        )
        proc.wait(timeout=120)

        with open(out_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    finally:
        for p in (py_path, out_path):
            try:
                os.unlink(p)
            except OSError:
                pass


@app.get("/api/pick/file")
def pick_file(title: str = Query("Select file"), filter: str = Query("all")):
    path = _run_picker("file", title, FILTER_MAP.get(filter, FILTER_MAP["all"]))
    return {"path": path}


@app.get("/api/pick/directory")
def pick_directory(title: str = Query("Select folder")):
    path = _run_picker("directory", title)
    return {"path": path}


# ---------------------------------------------------------------------------
# Credentials endpoint — reads from the tool's .env if present
# ---------------------------------------------------------------------------

@app.get("/api/credentials/five9")
def get_five9_credentials():
    env_file = TOOL_PATHS["five9.prompt_bulk_upload"] / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)
    return {
        "username": os.environ.get("FIVE9_USERNAME", ""),
        "password": os.environ.get("FIVE9_PASSWORD", ""),
        "domain": os.environ.get("FIVE9_DOMAIN", "api.five9.com"),
    }


# ---------------------------------------------------------------------------
# Five9 — Prompt Bulk Upload
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Approval-gated CCaaS configuration demo - deterministic stub mode only
# ---------------------------------------------------------------------------

class DemoAnalyzeRequest(BaseModel):
    discovery_template: str


class DemoToolCall(BaseModel):
    tool_name: str
    params: Dict[str, Any]


class DemoExecuteRequest(BaseModel):
    approved: bool = False
    planned_calls: List[DemoToolCall]


class PlaybookAgentRequest(BaseModel):
    playbook_path: str


class PlaybookAgentExecuteRequest(BaseModel):
    approved: bool = False
    mode: str = "dry_run"
    plan_id: str
    planned_calls: List[Dict[str, Any]]
    domain: str = "api.five9.com"
    username: Optional[str] = None
    password: Optional[str] = None


@app.post("/api/demo/analyze-requirements")
def analyze_demo_requirements(req: DemoAnalyzeRequest):
    try:
        return analyze_requirements(req.discovery_template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/demo/execute-stubs")
def execute_demo_stubs(req: DemoExecuteRequest):
    planned_calls = [
        call.model_dump() if hasattr(call, "model_dump") else call.dict()
        for call in req.planned_calls
    ]

    try:
        logs = execute_stub_plan(req.approved, planned_calls)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"logs": logs, "message": STUB_EXECUTION_MESSAGE}


@app.post("/api/agent/playbook/analyze")
def analyze_playbook_agent(req: PlaybookAgentRequest):
    try:
        return analyze_playbook(req.playbook_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/agent/playbook/upload-analyze")
def analyze_playbook_upload(
    file: UploadFile = File(...),
    ai_provider: str = Form("anthropic"),
    api_key: str = Form(""),
    model: str = Form(""),
    ai_required: bool = Form(False),
    preflight_mode: str = Form("stub"),
    preflight_approved: bool = Form(False),
    preflight_domain: str = Form("api.five9.com"),
    preflight_username: str = Form(""),
    preflight_password: str = Form(""),
):
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx playbooks are supported")

    resolved_preflight_mode = _form_value(preflight_mode, "stub") or "stub"
    if resolved_preflight_mode not in ("stub", "live"):
        raise HTTPException(status_code=400, detail="preflight_mode must be 'stub' or 'live'")

    preflight_client = None
    resolved_preflight_approved = _form_bool(preflight_approved, False)
    if resolved_preflight_mode == "live":
        if resolved_preflight_approved is not True:
            raise HTTPException(
                status_code=403,
                detail="Live Playbook Agent preflight requires explicit approval",
            )
        if not _form_value(preflight_username, "") or not _form_value(preflight_password, ""):
            raise HTTPException(
                status_code=400,
                detail="Username and password are required for live Playbook Agent preflight",
            )
        preflight_client = Five9ConfigClient(
            username=_form_value(preflight_username, ""),
            password=_form_value(preflight_password, ""),
            domain=_form_value(preflight_domain, "api.five9.com") or "api.five9.com",
        )

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / filename
            target.write_bytes(file.file.read())
            result = run_playbook_agent(
                target,
                ai_provider=_form_value(ai_provider, "anthropic"),
                api_key=_form_value(api_key, "") or None,
                model=_form_value(model, "") or None,
                preflight_mode=resolved_preflight_mode,
                preflight_approved=resolved_preflight_approved,
                preflight_client=preflight_client,
            )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Playbook Agent failed: {e}")

    plan_id = result["plan_id"]
    if _form_bool(ai_required, False) and result.get("ai_mode") == "fallback":
        messages = [
            item.get("message", str(item))
            for item in result.get("review_items", [])
            if isinstance(item, dict)
        ]
        detail = "AI interpretation failed"
        if messages:
            detail = f"{detail}: {messages[0]}"
        raise HTTPException(status_code=502, detail=detail)

    try:
        _validate_returned_agent_plan_arrays(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    AGENT_PLAN_STORE[plan_id] = result["proposed_write_plan"]
    result["source"] = result.get("parsed_playbook", {}).get("source", {"file_name": filename})
    result.pop("parsed_playbook", None)
    return result


def _validate_returned_agent_plan_arrays(result: dict[str, Any]) -> None:
    """Validate every tool-plan array before the browser can display or submit it."""
    result["ai_planned_calls"] = validate_planned_calls(result.get("ai_planned_calls", []))
    result["core_write_plan"] = validate_planned_calls(result.get("core_write_plan", []))
    result["proposed_ivr_script_plan"] = validate_ivr_script_plan(
        result.get("proposed_ivr_script_plan", [])
    )
    result["proposed_write_plan"] = validate_agent_executable_plan(
        result.get("proposed_write_plan", [])
    )


def _form_value(value: Any, default: str) -> str:
    if isinstance(value, str):
        return value.strip()
    return default


def _form_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


@app.post("/api/agent/playbook/execute")
def execute_playbook_agent(req: PlaybookAgentExecuteRequest):
    if req.approved is not True:
        raise HTTPException(status_code=403, detail="Agent execution requires explicit approval")
    if req.mode not in ("dry_run", "live"):
        raise HTTPException(status_code=400, detail="mode must be 'dry_run' or 'live'")

    expected_plan = AGENT_PLAN_STORE.get(req.plan_id)
    if expected_plan is None:
        raise HTTPException(status_code=400, detail="Unknown or expired agent plan_id")
    try:
        submitted_plan = validate_agent_executable_plan(req.planned_calls)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not plans_match(expected_plan, submitted_plan):
        raise HTTPException(
            status_code=400,
            detail="Submitted plan does not match the generated approved plan",
        )

    client = None
    if req.mode == "live":
        if not req.username or not req.password:
            raise HTTPException(status_code=400, detail="Live execution requires credentials")
        client = Five9ConfigClient(
            username=req.username,
            password=req.password,
            domain=req.domain,
        )

    try:
        core_calls = [
            call for call in submitted_plan if call["tool_name"] in ALLOWED_CORE_WRITE_TOOL_NAMES
        ]
        ivr_script_calls = [
            call for call in submitted_plan if call["tool_name"] == "five9_create_ivr_script"
        ]
        results = []
        if ivr_script_calls:
            results.extend(
                five9_ivr_scripts.execute_ivr_script_plan(
                    approved=req.approved,
                    planned_calls=ivr_script_calls,
                    mode=req.mode,
                    client=client,
                )
            )
        if core_calls:
            results.extend(
                five9_core_writes.execute_core_write_plan(
                    approved=req.approved,
                    planned_calls=core_calls,
                    mode=req.mode,
                    client=client,
                )
            )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    failed = sum(1 for result in results if result.get("result") == "failed")
    return {
        "results": results,
        "summary": {
            "total": len(results),
            "failed": failed,
            "mode": req.mode,
            "live": req.mode == "live",
            "plan_id": req.plan_id,
        },
    }


class PromptBulkUploadRequest(BaseModel):
    manifest_path: str
    wav_dir: str = "."
    domain: str = "api.five9.com"
    username: str
    password: str
    dry_run: bool = False


class Five9PreflightRequest(BaseModel):
    mode: str = "stub"
    approved: bool = False
    domain: str = "api.five9.com"
    username: Optional[str] = None
    password: Optional[str] = None
    include_skills: bool = True
    include_dispositions: bool = True
    include_prompts: bool = True
    include_campaigns: bool = True
    include_dnis: bool = True
    include_campaign_dnis: bool = True
    skill_name_pattern: Optional[str] = None
    disposition_name_pattern: Optional[str] = None
    prompt_name_pattern: Optional[str] = None
    campaign_name_pattern: Optional[str] = None
    campaign_type: Optional[str] = "inbound"
    select_unassigned_dnis: bool = False
    campaign_dnis_name: Optional[str] = None


class Five9CoreWriteCall(BaseModel):
    tool_name: str
    params: Dict[str, Any]


class Five9CoreWriteRequest(BaseModel):
    mode: str = "dry_run"
    approved: bool = False
    domain: str = "api.five9.com"
    username: Optional[str] = None
    password: Optional[str] = None
    planned_calls: List[Five9CoreWriteCall]


class Five9RollbackCall(BaseModel):
    tool_name: str
    params: Dict[str, Any]


class Five9RollbackRequest(BaseModel):
    mode: str = "dry_run"
    approved: bool = False
    domain: str = "api.five9.com"
    username: Optional[str] = None
    password: Optional[str] = None
    planned_calls: List[Five9RollbackCall]


class Five9ModifyCall(BaseModel):
    tool_name: str
    params: Dict[str, Any]


class Five9ModifyRequest(BaseModel):
    mode: str = "dry_run"
    approved: bool = False
    domain: str = "api.five9.com"
    username: Optional[str] = None
    password: Optional[str] = None
    planned_calls: List[Five9ModifyCall]


class Five9IvrScriptCall(BaseModel):
    tool_name: str
    params: Dict[str, Any]


class Five9IvrScriptRequest(BaseModel):
    mode: str = "dry_run"
    approved: bool = False
    domain: str = "api.five9.com"
    username: Optional[str] = None
    password: Optional[str] = None
    planned_calls: List[Five9IvrScriptCall]


class Five9IvrBuilderAnalyzeRequest(BaseModel):
    file_path: Optional[str] = None
    xml_text: Optional[str] = None
    script_name: Optional[str] = None


class Five9IvrBuilderPlanRequest(BaseModel):
    build_plan: Dict[str, Any]


class Five9IvrBuilderPaletteRequest(BaseModel):
    file_path: Optional[str] = None
    folder_path: Optional[str] = None


class Five9IvrBuilderCanvasRequest(BaseModel):
    canvas: Dict[str, Any]


class Five9IvrBuilderCertificationRequest(BaseModel):
    mode: str = "dry_run"
    approved: bool = False
    domain: str = "api.five9.com"
    username: Optional[str] = None
    password: Optional[str] = None
    module_types: Optional[List[str]] = None
    target_script_name: str = "ZZ_TEST_Codex_IVR_ModuleLab"


class Five9IvrBuilderDeployRequest(BaseModel):
    mode: str = "dry_run"
    approved: bool = False
    domain: str = "api.five9.com"
    username: Optional[str] = None
    password: Optional[str] = None
    script_name: str
    description: Optional[str] = None
    xml_definition: str


def _preflight_params(**params):
    return {
        key: value
        for key, value in params.items()
        if value is not None and value is not False
    }


def _run_preflight_read(results, tool_name, params, mode, callback):
    try:
        result = callback()
    except Exception as e:
        result = five9_preflight.build_tool_error_result(
            tool_name=tool_name,
            params=params,
            mode=mode,
            error=str(e),
        )
    results.append(result)
    return result


def _campaign_supports_dnis_lookup(campaign: Dict[str, Any]) -> bool:
    campaign_type = (
        campaign.get("type")
        or campaign.get("campaignType")
        or campaign.get("campaign_type")
    )
    if campaign_type is None:
        return True
    return str(campaign_type).lower() == "inbound"


@app.post("/api/run/five9/core-writes")
def run_five9_core_writes(req: Five9CoreWriteRequest):
    if req.mode not in ("dry_run", "live"):
        raise HTTPException(status_code=400, detail="mode must be 'dry_run' or 'live'")

    client = None
    if req.mode == "live":
        if req.approved is not True:
            raise HTTPException(
                status_code=403,
                detail="Live Five9 write calls require explicit approval",
            )
        if not req.username or not req.password:
            raise HTTPException(
                status_code=400,
                detail="Username and password are required for live Five9 writes",
            )
        client = Five9ConfigClient(
            username=req.username,
            password=req.password,
            domain=req.domain,
        )

    planned_calls = [
        call.model_dump() if hasattr(call, "model_dump") else call.dict()
        for call in req.planned_calls
    ]

    try:
        results = five9_core_writes.execute_core_write_plan(
            approved=req.approved,
            planned_calls=planned_calls,
            mode=req.mode,
            client=client,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "results": results,
        "summary": {
            "total": len(results),
            "failed": sum(1 for result in results if result.get("result") == "failed"),
            "mode": req.mode,
            "live": req.mode == "live",
        },
    }


@app.post("/api/run/five9/modify")
def run_five9_modify(req: Five9ModifyRequest):
    if req.mode not in ("dry_run", "live"):
        raise HTTPException(status_code=400, detail="mode must be 'dry_run' or 'live'")

    client = None
    if req.mode == "live":
        if req.approved is not True:
            raise HTTPException(
                status_code=403,
                detail="Live Five9 modify calls require explicit approval",
            )
        if not req.username or not req.password:
            raise HTTPException(
                status_code=400,
                detail="Username and password are required for live Five9 modify calls",
            )
        client = Five9ConfigClient(
            username=req.username,
            password=req.password,
            domain=req.domain,
        )

    planned_calls = [
        call.model_dump() if hasattr(call, "model_dump") else call.dict()
        for call in req.planned_calls
    ]

    try:
        results = five9_modify.execute_modify_plan(
            approved=req.approved,
            planned_calls=planned_calls,
            mode=req.mode,
            client=client,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "results": results,
        "summary": {
            "total": len(results),
            "failed": sum(1 for result in results if result.get("result") == "failed"),
            "mode": req.mode,
            "live": req.mode == "live",
        },
    }


@app.post("/api/run/five9/rollback")
def run_five9_rollback(req: Five9RollbackRequest):
    if req.mode not in ("dry_run", "live"):
        raise HTTPException(status_code=400, detail="mode must be 'dry_run' or 'live'")

    client = None
    if req.mode == "live":
        if req.approved is not True:
            raise HTTPException(
                status_code=403,
                detail="Live Five9 rollback calls require explicit approval",
            )
        if not req.username or not req.password:
            raise HTTPException(
                status_code=400,
                detail="Username and password are required for live Five9 rollback calls",
            )
        client = Five9ConfigClient(
            username=req.username,
            password=req.password,
            domain=req.domain,
        )

    planned_calls = [
        call.model_dump() if hasattr(call, "model_dump") else call.dict()
        for call in req.planned_calls
    ]

    try:
        results = five9_rollback.execute_rollback_plan(
            approved=req.approved,
            planned_calls=planned_calls,
            mode=req.mode,
            client=client,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "results": results,
        "summary": {
            "total": len(results),
            "failed": sum(1 for result in results if result.get("result") == "failed"),
            "mode": req.mode,
            "live": req.mode == "live",
        },
    }


@app.post("/api/run/five9/ivr-scripts")
def run_five9_ivr_scripts(req: Five9IvrScriptRequest):
    if req.mode not in ("dry_run", "live"):
        raise HTTPException(status_code=400, detail="mode must be 'dry_run' or 'live'")

    client = None
    if req.mode == "live":
        if req.approved is not True:
            raise HTTPException(
                status_code=403,
                detail="Live Five9 IVR script calls require explicit approval",
            )
        if not req.username or not req.password:
            raise HTTPException(
                status_code=400,
                detail="Username and password are required for live Five9 IVR script calls",
            )
        client = Five9ConfigClient(
            username=req.username,
            password=req.password,
            domain=req.domain,
        )

    planned_calls = [
        call.model_dump() if hasattr(call, "model_dump") else call.dict()
        for call in req.planned_calls
    ]

    try:
        results = five9_ivr_scripts.execute_ivr_script_plan(
            approved=req.approved,
            planned_calls=planned_calls,
            mode=req.mode,
            client=client,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "results": results,
        "summary": {
            "total": len(results),
            "failed": sum(1 for result in results if result.get("result") == "failed"),
            "mode": req.mode,
            "live": req.mode == "live",
        },
    }


@app.get("/api/run/five9/ivr-builder/catalog")
def get_five9_ivr_builder_catalog():
    return five9_ivr_builder.get_ivr_builder_catalog()


@app.post("/api/run/five9/ivr-builder/palette")
def get_five9_ivr_builder_palette(req: Five9IvrBuilderPaletteRequest):
    if req.file_path or req.folder_path:
        raise HTTPException(
            status_code=400,
            detail="Runtime IVR builder palette uses the sanitized compiler registry only",
        )
    return five9_ivr_builder.get_ivr_builder_palette()


@app.post("/api/run/five9/ivr-builder/module-manual")
def build_five9_ivr_builder_module_manual(req: Five9IvrBuilderPaletteRequest):
    raise HTTPException(
        status_code=410,
        detail="Offline Five9 IVR export analysis is developer-only and is not available from the app runtime",
    )


@app.post("/api/run/five9/ivr-builder/analyze-file")
def analyze_five9_ivr_builder_file(req: Five9IvrBuilderAnalyzeRequest):
    raise HTTPException(
        status_code=410,
        detail="Offline Five9 IVR export analysis is developer-only and is not available from the app runtime",
    )


@app.post("/api/run/five9/ivr-builder/analyze-palette")
def analyze_five9_ivr_builder_palette(req: Five9IvrBuilderAnalyzeRequest):
    raise HTTPException(
        status_code=410,
        detail="Offline Five9 IVR export analysis is developer-only and is not available from the app runtime",
    )


@app.post("/api/run/five9/ivr-builder/validate-plan")
def validate_five9_ivr_builder_plan(req: Five9IvrBuilderPlanRequest):
    return five9_ivr_builder.validate_build_plan(req.build_plan)


@app.post("/api/run/five9/ivr-builder/visualize-plan")
def visualize_five9_ivr_builder_plan(req: Five9IvrBuilderPlanRequest):
    return five9_ivr_builder.visualize_build_plan(req.build_plan)


@app.post("/api/run/five9/ivr-builder/validate-canvas")
def validate_five9_ivr_builder_canvas(req: Five9IvrBuilderCanvasRequest):
    return five9_ivr_builder.validate_visual_canvas(req.canvas)


@app.post("/api/run/five9/ivr-builder/canvas-to-plan")
def convert_five9_ivr_builder_canvas_to_plan(req: Five9IvrBuilderCanvasRequest):
    try:
        return five9_ivr_builder.visual_canvas_to_build_plan(req.canvas)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/run/five9/ivr-builder/compile")
def compile_five9_ivr_builder_plan(req: Five9IvrBuilderPlanRequest):
    try:
        return five9_ivr_builder.compile_simple_menu_ivr(req.build_plan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/run/five9/ivr-builder/compile-canvas")
def compile_five9_ivr_builder_canvas(req: Five9IvrBuilderCanvasRequest):
    try:
        return five9_ivr_builder.compile_canvas_ivr(req.canvas)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/run/five9/ivr-builder/certify")
def certify_five9_ivr_builder_modules(req: Five9IvrBuilderCertificationRequest):
    if req.mode not in ("dry_run", "live"):
        raise HTTPException(status_code=400, detail="mode must be 'dry_run' or 'live'")
    client = None
    if req.mode == "live":
        if req.approved is not True:
            raise HTTPException(
                status_code=403,
                detail="Live Five9 IVR module certification requires explicit approval",
            )
        if not req.username or not req.password:
            raise HTTPException(
                status_code=400,
                detail="Username and password are required for live Five9 IVR module certification",
            )
        client = Five9ConfigClient(
            username=req.username,
            password=req.password,
            domain=req.domain,
        )
    try:
        return five9_ivr_builder.certify_module_factories(
            module_types=req.module_types,
            mode=req.mode,
            approved=req.approved,
            client=client,
            target_script_name=req.target_script_name,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/run/five9/ivr-builder/deploy")
def deploy_five9_ivr_builder_script(req: Five9IvrBuilderDeployRequest):
    if req.mode not in ("dry_run", "live"):
        raise HTTPException(status_code=400, detail="mode must be 'dry_run' or 'live'")
    if not req.script_name or not req.script_name.strip():
        raise HTTPException(status_code=400, detail="script_name is required")
    if not req.xml_definition or not req.xml_definition.strip():
        raise HTTPException(status_code=400, detail="xml_definition is required")

    client = None
    if req.mode == "live":
        if req.approved is not True:
            raise HTTPException(
                status_code=403,
                detail="Live Five9 IVR builder deploy requires explicit approval",
            )
        if not req.username or not req.password:
            raise HTTPException(
                status_code=400,
                detail="Username and password are required for live Five9 IVR builder deploy",
            )
        client = Five9ConfigClient(
            username=req.username,
            password=req.password,
            domain=req.domain,
        )

    try:
        results = five9_ivr_scripts.execute_ivr_script_upsert(
            approved=req.approved,
            name=req.script_name.strip(),
            description=req.description,
            xml_definition=req.xml_definition,
            mode=req.mode,
            client=client,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "results": results,
        "summary": {
            "total": len(results),
            "failed": sum(1 for result in results if result.get("result") == "failed"),
            "mode": req.mode,
            "live": req.mode == "live",
        },
    }


@app.post("/api/run/five9/preflight")
def run_five9_preflight(req: Five9PreflightRequest):
    if req.mode not in ("stub", "live"):
        raise HTTPException(status_code=400, detail="mode must be 'stub' or 'live'")

    client = None
    if req.mode == "live":
        if req.approved is not True:
            raise HTTPException(
                status_code=403,
                detail="Live Five9 read calls require explicit approval",
            )
        if not req.username or not req.password:
            raise HTTPException(
                status_code=400,
                detail="Username and password are required for live Five9 reads",
            )
        client = Five9ConfigClient(
            username=req.username,
            password=req.password,
            domain=req.domain,
        )

    results = []
    if req.include_skills:
        _run_preflight_read(
            results,
            "five9_get_skills",
            _preflight_params(name_pattern=req.skill_name_pattern),
            req.mode,
            lambda: five9_preflight.five9_get_skills(
                    name_pattern=req.skill_name_pattern,
                    mode=req.mode,
                    approved=req.approved,
                    client=client,
            ),
        )
    if req.include_dispositions:
        _run_preflight_read(
            results,
            "five9_get_dispositions",
            _preflight_params(name_pattern=req.disposition_name_pattern),
            req.mode,
            lambda: five9_preflight.five9_get_dispositions(
                    name_pattern=req.disposition_name_pattern,
                    mode=req.mode,
                    approved=req.approved,
                    client=client,
            ),
        )
    if req.include_prompts:
        _run_preflight_read(
            results,
            "five9_get_prompts",
            _preflight_params(name_pattern=req.prompt_name_pattern),
            req.mode,
            lambda: five9_preflight.five9_get_prompts(
                    name_pattern=req.prompt_name_pattern,
                    mode=req.mode,
                    approved=req.approved,
                    client=client,
            ),
        )
    campaign_result = None
    if req.include_campaigns or (req.include_campaign_dnis and not req.campaign_dnis_name):
        campaign_params = _preflight_params(
            name_pattern=req.campaign_name_pattern,
            campaign_type=req.campaign_type or None,
        )
        campaign_result = _run_preflight_read(
            results if req.include_campaigns else [],
            "five9_get_campaigns",
            campaign_params,
            req.mode,
            lambda: five9_preflight.five9_get_campaigns(
                name_pattern=req.campaign_name_pattern,
                campaign_type=req.campaign_type or None,
                mode=req.mode,
                approved=req.approved,
                client=client,
            ),
        )
    if req.include_dnis:
        _run_preflight_read(
            results,
            "five9_get_dnis_list",
            _preflight_params(select_unassigned=req.select_unassigned_dnis),
            req.mode,
            lambda: five9_preflight.five9_get_dnis_list(
                    select_unassigned=req.select_unassigned_dnis,
                    mode=req.mode,
                    approved=req.approved,
                    client=client,
            ),
        )
    if req.include_campaign_dnis:
        campaign_names = []
        if req.campaign_dnis_name:
            campaign_names = [req.campaign_dnis_name]
        elif campaign_result and campaign_result.get("result") == "success":
            campaign_names = [
                campaign["name"]
                for campaign in campaign_result["data"]
                if (
                    isinstance(campaign, dict)
                    and campaign.get("name")
                    and _campaign_supports_dnis_lookup(campaign)
                )
            ]

        for campaign_name in campaign_names:
            _run_preflight_read(
                results,
                "five9_get_campaign_dnis_list",
                {"campaign_name": campaign_name},
                req.mode,
                lambda campaign_name=campaign_name: five9_preflight.five9_get_campaign_dnis_list(
                        campaign_name=campaign_name,
                        mode=req.mode,
                        approved=req.approved,
                        client=client,
                ),
            )

    return {
        "results": results,
        "summary": {
            "total": len(results),
            "failed": sum(1 for result in results if result.get("result") == "failed"),
            "mode": req.mode,
            "live": req.mode == "live",
        },
    }


@app.post("/api/run/five9/prompt-bulk-upload")
def run_prompt_bulk_upload(req: PromptBulkUploadRequest):
    tool_path = str(TOOL_PATHS["five9.prompt_bulk_upload"])
    if tool_path not in sys.path:
        sys.path.insert(0, tool_path)

    try:
        from five9_prompts import Five9PromptClient, bulk_upload
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Failed to import tool module: {e}")

    try:
        if req.dry_run:
            results = bulk_upload(
                client=None,
                manifest_path=req.manifest_path,
                wav_dir=req.wav_dir,
                dry_run=True,
            )
        else:
            client = Five9PromptClient(
                username=req.username,
                password=req.password,
                domain=req.domain,
            )
            results = bulk_upload(
                client=client,
                manifest_path=req.manifest_path,
                wav_dir=req.wav_dir,
                dry_run=False,
            )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    rows = [
        {
            "name": r.name,
            "type": r.prompt_type,
            "action": r.action,
            "error": r.error or "",
        }
        for r in results
    ]

    summary = {
        "total": len(rows),
        "created": sum(1 for r in rows if r["action"] == "created"),
        "updated": sum(1 for r in rows if r["action"] == "updated"),
        "skipped": sum(1 for r in rows if r["action"] == "skipped"),
        "failed": sum(1 for r in rows if r["action"] == "failed"),
    }

    return {"results": rows, "summary": summary}


# ---------------------------------------------------------------------------
# Five9 — Prompt Bulk Upload (WAV folder mode)
# ---------------------------------------------------------------------------

class WavDirUploadRequest(BaseModel):
    wav_dir: str
    domain: str = "api.five9.com"
    username: str
    password: str
    overwrite: bool = False
    dry_run: bool = False


@app.post("/api/run/five9/prompt-bulk-upload-wav")
def run_wav_dir_upload(req: WavDirUploadRequest):
    tool_path = str(TOOL_PATHS["five9.prompt_bulk_upload"])
    if tool_path not in sys.path:
        sys.path.insert(0, tool_path)

    try:
        from five9_prompts import Five9PromptClient, bulk_upload_wav_dir
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Failed to import tool module: {e}")

    try:
        if req.dry_run:
            results = bulk_upload_wav_dir(
                client=None,
                wav_dir=req.wav_dir,
                overwrite=req.overwrite,
                dry_run=True,
            )
        else:
            client = Five9PromptClient(
                username=req.username,
                password=req.password,
                domain=req.domain,
            )
            results = bulk_upload_wav_dir(
                client=client,
                wav_dir=req.wav_dir,
                overwrite=req.overwrite,
                dry_run=False,
            )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    rows = [
        {"name": r.name, "type": r.prompt_type, "action": r.action, "error": r.error or ""}
        for r in results
    ]
    summary = {
        "total": len(rows),
        "created": sum(1 for r in rows if r["action"] == "created"),
        "updated": sum(1 for r in rows if r["action"] == "updated"),
        "skipped": sum(1 for r in rows if r["action"] == "skipped"),
        "failed":  sum(1 for r in rows if r["action"] == "failed"),
    }
    return {"results": rows, "summary": summary}


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    reload_dirs = [str(Path(__file__).parent)] + [str(p) for p in TOOL_PATHS.values()]
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True, reload_dirs=reload_dirs)
