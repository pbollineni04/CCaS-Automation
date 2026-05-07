"""
app.py — CCaaS Automation Tools UI Backend

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
from fastapi import FastAPI, HTTPException, Query
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

TOOL_PATHS = {
    "five9.prompt_bulk_upload": ROOT / "src" / "tools" / "Five9" / "Prompt_Management" / "Prompt_Bulk_Upload",
}

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="CCaaS Automation Tools")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


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


class PromptBulkUploadRequest(BaseModel):
    manifest_path: str
    wav_dir: str = "."
    domain: str = "api.five9.com"
    username: str
    password: str
    dry_run: bool = False


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
