"""Five9 Studio prompt audio flow.

Creates Studio prompt content, retrieves generated prompt audio, and reuses the
existing Five9 VCC WAV upload client for the final upload step.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

import requests


DEFAULT_STUDIO_BASE_URL = "https://api.us7.studioportal.io"
DEFAULT_STUDIO_SCOPE = "ac"


@dataclass
class StudioAudioResult:
    audio_bytes: Optional[bytes] = None
    metadata: Optional[dict[str, Any]] = None
    content_type: str = ""


class StudioPromptClient:
    def __init__(
        self,
        base_url: str = DEFAULT_STUDIO_BASE_URL,
        api_key: str = "",
        scope: str = DEFAULT_STUDIO_SCOPE,
        scope_id: str = "",
        session: Any = None,
    ):
        self.base_url = _normalize_base_url(base_url or DEFAULT_STUDIO_BASE_URL)
        self.api_key = api_key
        self.scope = scope or DEFAULT_STUDIO_SCOPE
        self.scope_id = str(scope_id or "")
        self._session = session or requests.Session()

    def _headers(self) -> dict[str, str]:
        return {
            "studio-api-key": self.api_key,
            "scope": self.scope,
            "scope-id": self.scope_id,
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def list_tts_voices(self) -> list[dict[str, Any]]:
        response = self._session.get(
            self._url("/api/prompt/tts-voices"),
            headers=self._headers(),
            timeout=60,
        )
        if response.status_code in {401, 403}:
            fallback = self._session.get(
                self._url("/api/prompt/languages"),
                headers=self._headers(),
                timeout=60,
            )
            fallback.raise_for_status()
            return _normalize_voices(fallback.json())
        response.raise_for_status()
        return _normalize_voices(response.json())

    def list_prompts(self) -> list[dict[str, Any]]:
        response = self._session.get(
            self._url("/api/prompt/prompts"),
            headers=self._headers(),
            params={
                "per_page": 200,
                "page": 1,
                "orderBy": "prompt_id",
                "sortedBy": "desc",
                "folder_id": 0,
                "task_id": -1,
                "hide_system": "false",
                "prompt_type": "IVA",
            },
            timeout=60,
        )
        response.raise_for_status()
        return _normalize_prompts(response.json())

    def create_prompt(
        self,
        prompt_name: str,
        prompt_text: str,
        voice: Mapping[str, Any],
        folder_id: int = 0,
    ) -> dict[str, Any]:
        payload = _prompt_payload(prompt_name, prompt_text, voice, folder_id=folder_id)
        response = self._session.post(
            self._url("/api/prompt/prompts"),
            headers=self._headers(),
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def update_prompt(
        self,
        prompt_id: Any,
        prompt_name: str,
        prompt_text: str,
        voice: Mapping[str, Any],
        folder_id: int = 0,
    ) -> dict[str, Any]:
        payload = _prompt_payload(prompt_name, prompt_text, voice, folder_id=folder_id)
        payload["prompt_id"] = prompt_id
        payload["prompt_type"] = "IVA"
        payload["is_archived"] = 0
        response = self._session.put(
            self._url(f"/api/prompt/prompts/{prompt_id}"),
            headers=self._headers(),
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def get_prompt_audio(self, prompt_text: str, tts_voice_id: Any) -> StudioAudioResult:
        response = self._session.post(
            self._url("/api/speech/get_prompt_audio"),
            headers=self._headers(),
            json={"prompt_text": prompt_text, "tts_voice_id": tts_voice_id},
            timeout=120,
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if _is_audio_response(content_type, response.content):
            return StudioAudioResult(audio_bytes=response.content, content_type=content_type)
        payload = response.json()
        return StudioAudioResult(metadata=_first_mapping(payload), content_type=content_type)

    def download_wav_file(self, metadata: Mapping[str, Any]) -> bytes:
        response = self._session.post(
            self._url("/api/api/file-download-from-url"),
            headers=self._headers(),
            json=dict(metadata),
            timeout=120,
        )
        response.raise_for_status()
        return response.content


def run_studio_prompt_flow(
    *,
    studio_client: StudioPromptClient,
    vcc_client: Any,
    prompts: list[Mapping[str, Any]],
    voice: Mapping[str, Any],
    output_dir: str | Path,
    approved: bool,
    overwrite: bool = False,
    voice_overrides: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> dict[str, Any]:
    if not approved:
        raise PermissionError("Studio prompt flow requires explicit approval")
    if not prompts:
        raise ValueError("At least one prompt is required")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    voice_overrides = voice_overrides or {}

    studio_prompts = {
        str(item.get("prompt_name") or item.get("name") or "").strip(): item
        for item in studio_client.list_prompts()
        if str(item.get("prompt_name") or item.get("name") or "").strip()
    }
    vcc_existing = set(vcc_client.get_existing_prompts())

    rows: list[dict[str, Any]] = []
    for prompt in prompts:
        name = str(prompt.get("prompt_name") or prompt.get("name") or "").strip()
        text = str(prompt.get("text") or prompt.get("prompt_text") or "").strip()
        if not name or not text:
            rows.append(_row(name or "(missing)", "failed", error="prompt_name and text are required"))
            continue

        selected_voice = dict(voice_overrides.get(name) or voice or {})
        voice_id = selected_voice.get("tts_voice_id")
        if voice_id in (None, ""):
            rows.append(_row(name, "failed", error="tts_voice_id is required"))
            continue

        studio_existing = studio_prompts.get(name)
        vcc_exists = name in vcc_existing
        if (studio_existing or vcc_exists) and not overwrite:
            rows.append(_row(name, "skipped", studio_exists=bool(studio_existing), vcc_exists=vcc_exists))
            continue

        try:
            if studio_existing:
                studio_response = studio_client.update_prompt(
                    studio_existing.get("prompt_id") or studio_existing.get("id"),
                    name,
                    text,
                    selected_voice,
                )
                studio_action = "updated"
            else:
                studio_response = studio_client.create_prompt(name, text, selected_voice)
                studio_action = "created"

            audio = studio_client.get_prompt_audio(text, voice_id)
            audio_bytes = audio.audio_bytes
            if audio_bytes is None and audio.metadata:
                audio_bytes = studio_client.download_wav_file(audio.metadata)
            if not audio_bytes:
                raise RuntimeError("Studio did not return prompt audio")

            wav_path = output_path / f"{_safe_filename(name)}.wav"
            wav_path.write_bytes(audio_bytes)

            if vcc_exists and overwrite:
                vcc_result = vcc_client.modify_prompt_wav(name, str(wav_path))
            else:
                vcc_result = vcc_client.add_prompt_wav(name, str(wav_path))

            action = "updated" if studio_action == "updated" or getattr(vcc_result, "action", "") == "updated" else "created"
            rows.append(
                _row(
                    name,
                    action,
                    wav_path=str(wav_path),
                    studio_action=studio_action,
                    vcc_action=getattr(vcc_result, "action", ""),
                    studio_prompt_id=_prompt_id(studio_response),
                )
            )
        except Exception as exc:  # keep processing remaining prompts
            rows.append(_row(name, "failed", error=str(exc)))

    return {"results": rows, "summary": _summary(rows), "output_dir": str(output_path)}


def save_audio_probe(
    *,
    studio_client: StudioPromptClient,
    prompt_text: str,
    voice: Mapping[str, Any],
    output_dir: str | Path,
) -> dict[str, Any]:
    voice_id = voice.get("tts_voice_id")
    if voice_id in (None, ""):
        raise ValueError("tts_voice_id is required")
    audio = studio_client.get_prompt_audio(prompt_text, voice_id)
    audio_bytes = audio.audio_bytes
    source = "direct_audio"
    if audio_bytes is None and audio.metadata:
        audio_bytes = studio_client.download_wav_file(audio.metadata)
        source = "download_metadata"
    if not audio_bytes:
        raise RuntimeError("Studio did not return prompt audio")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    wav_path = output_path / "studio-audio-probe.wav"
    wav_path.write_bytes(audio_bytes)
    return {
        "source": source,
        "content_type": audio.content_type,
        "wav_path": str(wav_path),
        "bytes": len(audio_bytes),
        "metadata": audio.metadata or {},
    }


def _prompt_payload(
    prompt_name: str,
    prompt_text: str,
    voice: Mapping[str, Any],
    folder_id: int = 0,
) -> dict[str, Any]:
    voice_name = str(voice.get("voice_name") or voice.get("tts_label") or voice.get("label") or "Default Voice")
    prompt_value = {
        "tts_voice_id": voice.get("tts_voice_id"),
        "tts_value": prompt_text,
        "file_url": "",
        "voice_name": voice_name,
        "file_path": "",
    }
    if voice.get("provider"):
        prompt_value["provider"] = voice.get("provider")
    return {
        "prompt_name": prompt_name,
        "prompt_values": [prompt_value],
        "default_tts_value": prompt_text,
        "default_voice_name": voice_name,
        "default_voice_audio_url": "",
        "default_voice_file_path": "",
        "default_voice_uploaded_file_name": "",
        "folder_id": folder_id,
        "guard_name": "admin",
    }


def _normalize_base_url(base_url: str) -> str:
    cleaned = str(base_url or DEFAULT_STUDIO_BASE_URL).strip().rstrip("/")
    return cleaned[:-4] if cleaned.endswith("/api") else cleaned


def _normalize_voices(payload: Any) -> list[dict[str, Any]]:
    values = _list_from_payload(payload, ("data", "voices", "tts_voices", "return"))
    voices = []
    for item in values:
        if not isinstance(item, Mapping):
            continue
        voice_id = item.get("tts_voice_id") or item.get("id") or item.get("voice_id")
        if voice_id in (None, ""):
            continue
        voice_name = item.get("voice_name") or item.get("tts_label") or item.get("label") or str(voice_id)
        voices.append(
            {
                "tts_voice_id": voice_id,
                "voice_name": voice_name,
                "tts_label": item.get("tts_label") or voice_name,
                "provider": item.get("provider") or item.get("tts_provider") or "",
                "language": item.get("language") or item.get("lang") or item.get("locale") or "",
            }
        )
    return voices


def _normalize_prompts(payload: Any) -> list[dict[str, Any]]:
    values = _list_from_payload(payload, ("data", "prompts", "items", "return"))
    prompts = []
    for item in values:
        if isinstance(item, Mapping):
            prompts.append(dict(item))
    return prompts


def _list_from_payload(payload: Any, keys: tuple[str, ...]) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, Mapping):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, Mapping):
            nested = _list_from_payload(value, keys)
            if nested:
                return nested
            flattened = []
            for nested_value in value.values():
                if isinstance(nested_value, list):
                    flattened.extend(nested_value)
            if flattened:
                return flattened
    return []


def _first_mapping(payload: Any) -> dict[str, Any]:
    if isinstance(payload, Mapping):
        if "data" in payload and isinstance(payload["data"], Mapping):
            return dict(payload["data"])
        return dict(payload)
    if isinstance(payload, list) and payload and isinstance(payload[0], Mapping):
        return dict(payload[0])
    return {}


def _is_audio_response(content_type: str, content: bytes) -> bool:
    lowered = content_type.lower()
    return lowered.startswith("audio/") or content.startswith(b"RIFF")


def _row(name: str, action: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "type": "wav", "action": action, **extra}


def _summary(rows: list[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "total": len(rows),
        "created": sum(1 for row in rows if row.get("action") == "created"),
        "updated": sum(1 for row in rows if row.get("action") == "updated"),
        "skipped": sum(1 for row in rows if row.get("action") == "skipped"),
        "failed": sum(1 for row in rows if row.get("action") == "failed"),
    }


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_. -]+", "_", value).strip(" .")
    return cleaned or "prompt"


def _prompt_id(response: Mapping[str, Any]) -> Any:
    if "prompt_id" in response:
        return response["prompt_id"]
    data = response.get("data")
    if isinstance(data, Mapping):
        return data.get("prompt_id") or data.get("id")
    return response.get("id")
