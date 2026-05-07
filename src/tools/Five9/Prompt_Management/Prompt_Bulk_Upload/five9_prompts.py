"""
five9_prompts.py — Five9 Prompt Management Core Module

Uses raw SOAP over HTTPS — no WSDL parsing, no zeep dependency.
Importable by the automation agent system.
"""

import base64
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth
from lxml import etree


# ---------------------------------------------------------------------------
# SOAP constants
# ---------------------------------------------------------------------------

ENDPOINT = "https://{domain}/wsadmin/v13/AdminWebService"
_SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
_SER_NS  = "http://service.admin.ws.five9.com/"
_HEADERS = {"Content-Type": "text/xml;charset=UTF-8", "SOAPAction": '""'}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _esc(s: str) -> str:
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _envelope(method: str, inner_xml: str) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<soapenv:Envelope xmlns:soapenv="{_SOAP_NS}" xmlns:ser="{_SER_NS}">'
        f'<soapenv:Header/>'
        f'<soapenv:Body>'
        f'<ser:{method}>{inner_xml}</ser:{method}>'
        f'</soapenv:Body>'
        f'</soapenv:Envelope>'
    )


def _prompt_xml(name: str, description: str = "") -> str:
    desc = f"<description>{_esc(description)}</description>" if description else ""
    return f"<prompt>{desc}<name>{_esc(name)}</name></prompt>"


def _tts_xml(text: str, voice: Optional[str] = None) -> str:
    v = f"<voice>{_esc(voice)}</voice>" if voice else ""
    return f"<ttsInfo><text>{_esc(text)}</text>{v}</ttsInfo>"


def _check_fault(root: etree._Element) -> Optional[str]:
    fault = root.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Fault")
    if fault is None:
        fault = root.find(".//Fault")
    if fault is not None:
        msg = fault.findtext("faultstring") or fault.findtext("message") or "SOAP fault"
        return msg
    return None


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class OperationResult:
    name: str
    action: str          # "created" | "updated" | "skipped" | "failed"
    prompt_type: str = ""
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class Five9PromptClient:
    def __init__(self, username: str, password: str, domain: str = "api.five9.com"):
        self._url = ENDPOINT.format(domain=domain)
        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(username, password)
        self._session.headers.update(_HEADERS)

    def _call(self, method: str, inner_xml: str) -> etree._Element:
        body = _envelope(method, inner_xml)
        resp = self._session.post(self._url, data=body.encode("utf-8"), timeout=60)
        root = etree.fromstring(resp.content)
        fault = _check_fault(root)
        if fault:
            raise RuntimeError(fault)
        return root

    def get_existing_prompts(self) -> set:
        root = self._call("getPrompts", "")
        names = set()
        for el in root.iter("return"):
            name = el.findtext("name")
            if name:
                names.add(name)
        return names

    def add_prompt_wav(self, name: str, wav_path: str, description: str = "") -> OperationResult:
        try:
            with open(wav_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            inner = _prompt_xml(name, description) + f"<wavFile>{b64}</wavFile>"
            self._call("addPromptWavInline", inner)
            return OperationResult(name=name, action="created", prompt_type="wav")
        except Exception as e:
            return OperationResult(name=name, action="failed", prompt_type="wav", error=str(e))

    def add_prompt_tts(self, name: str, text: str, description: str = "", voice: Optional[str] = None) -> OperationResult:
        try:
            inner = _prompt_xml(name, description) + _tts_xml(text, voice)
            self._call("addPromptTTS", inner)
            return OperationResult(name=name, action="created", prompt_type="tts")
        except Exception as e:
            return OperationResult(name=name, action="failed", prompt_type="tts", error=str(e))

    def modify_prompt_wav(self, name: str, wav_path: str, description: str = "") -> OperationResult:
        try:
            with open(wav_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            inner = _prompt_xml(name, description) + f"<wavFile>{b64}</wavFile>"
            self._call("modifyPromptWavInline", inner)
            return OperationResult(name=name, action="updated", prompt_type="wav")
        except Exception as e:
            return OperationResult(name=name, action="failed", prompt_type="wav", error=str(e))

    def modify_prompt_tts(self, name: str, text: str, description: str = "", voice: Optional[str] = None) -> OperationResult:
        try:
            inner = _prompt_xml(name, description) + _tts_xml(text, voice)
            self._call("modifyPromptTTS", inner)
            return OperationResult(name=name, action="updated", prompt_type="tts")
        except Exception as e:
            return OperationResult(name=name, action="failed", prompt_type="tts", error=str(e))

    def delete_prompt(self, name: str) -> OperationResult:
        try:
            self._call("deletePrompt", f"<name>{_esc(name)}</name>")
            return OperationResult(name=name, action="deleted", prompt_type="unknown")
        except Exception as e:
            return OperationResult(name=name, action="failed", prompt_type="unknown", error=str(e))


# ---------------------------------------------------------------------------
# Bulk operations
# ---------------------------------------------------------------------------

def _parse_manifest(manifest_path: str) -> list[dict]:
    rows = []
    with open(manifest_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            row["_line"] = i
            rows.append(row)
    return rows


def _validate_rows(rows: list[dict], wav_dir: str) -> list[str]:
    errors = []
    for row in rows:
        line = row["_line"]
        name = row.get("name", "").strip()
        prompt_type = row.get("type", "").strip().lower()
        source = row.get("source", "").strip()

        if not name:
            errors.append(f"Line {line}: missing 'name'")
        if prompt_type not in ("wav", "tts"):
            errors.append(f"Line {line} ({name}): 'type' must be 'wav' or 'tts', got '{prompt_type}'")
        if not source:
            errors.append(f"Line {line} ({name}): 'source' is empty")
        elif prompt_type == "wav":
            wav_path = Path(wav_dir) / source if not Path(source).is_absolute() else Path(source)
            if not wav_path.exists():
                errors.append(f"Line {line} ({name}): WAV file not found: {wav_path}")
            elif not wav_path.is_file():
                errors.append(f"Line {line} ({name}): path is not a file: {wav_path}")
    return errors


def bulk_upload_wav_dir(
    client: Five9PromptClient,
    wav_dir: str,
    overwrite: bool = False,
    dry_run: bool = False,
) -> list[OperationResult]:
    """Upload all WAV files in a directory. Prompt name = filename without extension."""
    wav_files = sorted(Path(wav_dir).glob("*.wav"))

    if not wav_files:
        return [OperationResult(name="(none)", action="failed", prompt_type="wav",
                                error=f"No .wav files found in: {wav_dir}")]

    if dry_run:
        return [
            OperationResult(
                name=f.stem,
                action="[dry-run] would create or update" if overwrite else "[dry-run] would create or skip",
                prompt_type="wav",
            )
            for f in wav_files
        ]

    existing = client.get_existing_prompts()
    results = []

    for wav_path in wav_files:
        name = wav_path.stem
        exists = name in existing

        if exists and not overwrite:
            results.append(OperationResult(name=name, action="skipped", prompt_type="wav"))
            continue

        if exists:
            result = client.modify_prompt_wav(name, str(wav_path))
        else:
            result = client.add_prompt_wav(name, str(wav_path))

        results.append(result)

    return results


def bulk_upload(
    client: Five9PromptClient,
    manifest_path: str,
    wav_dir: str = ".",
    dry_run: bool = False,
) -> list[OperationResult]:
    rows = _parse_manifest(manifest_path)
    validation_errors = _validate_rows(rows, wav_dir)

    if validation_errors:
        return [OperationResult(name=err, action="failed", error="validation")
                for err in validation_errors]

    if dry_run:
        results = []
        for row in rows:
            name = row["name"].strip()
            prompt_type = row["type"].strip().lower()
            overwrite = row.get("overwrite", "false").strip().lower() == "true"
            results.append(OperationResult(
                name=name,
                action="[dry-run] would create or update" if overwrite else "[dry-run] would create or skip",
                prompt_type=prompt_type,
            ))
        return results

    existing = client.get_existing_prompts()
    results = []

    for row in rows:
        name = row["name"].strip()
        prompt_type = row["type"].strip().lower()
        source = row["source"].strip()
        description = row.get("description", "").strip()
        overwrite = row.get("overwrite", "false").strip().lower() == "true"
        exists = name in existing

        if exists and not overwrite:
            results.append(OperationResult(name=name, action="skipped", prompt_type=prompt_type))
            continue

        if prompt_type == "wav":
            wav_path = str(Path(wav_dir) / source) if not Path(source).is_absolute() else source
            if exists:
                result = client.modify_prompt_wav(name, wav_path, description)
            else:
                result = client.add_prompt_wav(name, wav_path, description)
        else:
            if exists:
                result = client.modify_prompt_tts(name, source, description)
            else:
                result = client.add_prompt_tts(name, source, description)

        results.append(result)

    return results
