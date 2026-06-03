import json
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SAMPLE_PLAYBOOK = (
    ROOT
    / "outputs"
    / "playbook_template_work"
    / "Five9 Voice Implementation Playbook Template - Jacuzzi Fully Converted.xlsx"
)


class FakeJsonResponse:
    def __init__(self, payload, content=b"", headers=None, status_code=200):
        self._payload = payload
        self.content = content
        self.headers = headers or {"Content-Type": "application/json"}
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeStudioSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.responses.pop(0)

    def put(self, url, **kwargs):
        self.calls.append(("PUT", url, kwargs))
        return self.responses.pop(0)


class FakeVccClient:
    def __init__(self, existing=None):
        self.existing = set(existing or [])
        self.calls = []

    def get_existing_prompts(self):
        self.calls.append(("get_existing_prompts", {}))
        return set(self.existing)

    def add_prompt_wav(self, name, wav_path, description=""):
        self.calls.append(("add_prompt_wav", {"name": name, "wav_path": wav_path, "description": description}))
        return self._result(name, "created")

    def modify_prompt_wav(self, name, wav_path, description=""):
        self.calls.append(("modify_prompt_wav", {"name": name, "wav_path": wav_path, "description": description}))
        return self._result(name, "updated")

    def _result(self, name, action):
        class Result:
            prompt_type = "wav"
            error = None

            def __init__(self, name, action):
                self.name = name
                self.action = action

        return Result(name, action)


class StudioPromptClientTests(unittest.TestCase):
    def test_client_sends_required_studio_headers_and_normalizes_voices(self):
        from src.tools.Five9.Prompt_Management.Prompt_Bulk_Upload.studio_prompts import StudioPromptClient

        session = FakeStudioSession([
            FakeJsonResponse({"data": [{"tts_voice_id": 100, "voice_name": "Amanda", "tts_label": "Amanda"}]})
        ])
        client = StudioPromptClient(
            base_url="https://api.us7.studioportal.io",
            api_key="secret-key",
            scope="ac",
            scope_id="42",
            session=session,
        )

        voices = client.list_tts_voices()

        self.assertEqual(voices[0]["tts_voice_id"], 100)
        self.assertEqual(voices[0]["voice_name"], "Amanda")
        method, url, kwargs = session.calls[0]
        self.assertEqual(method, "GET")
        self.assertEqual(url, "https://api.us7.studioportal.io/api/prompt/tts-voices")
        self.assertEqual(kwargs["headers"]["studio-api-key"], "secret-key")
        self.assertEqual(kwargs["headers"]["scope"], "ac")
        self.assertEqual(kwargs["headers"]["scope-id"], "42")

    def test_client_accepts_doc_style_eu_base_url_that_already_includes_api(self):
        from src.tools.Five9.Prompt_Management.Prompt_Bulk_Upload.studio_prompts import StudioPromptClient

        session = FakeStudioSession([FakeJsonResponse({"data": []})])
        client = StudioPromptClient(
            base_url="https://api.prod.eu.five9.net/studio-backend/api/",
            api_key="secret-key",
            scope="ac",
            scope_id="45",
            session=session,
        )

        client.list_tts_voices()

        _, url, _ = session.calls[0]
        self.assertEqual(
            url,
            "https://api.prod.eu.five9.net/studio-backend/api/prompt/tts-voices",
        )

    def test_client_falls_back_to_languages_when_tts_voices_is_forbidden(self):
        from src.tools.Five9.Prompt_Management.Prompt_Bulk_Upload.studio_prompts import StudioPromptClient

        session = FakeStudioSession([
            FakeJsonResponse(
                {"message": "User does not have permission to perform this action."},
                status_code=403,
            ),
            FakeJsonResponse(
                {
                    "data": {
                        "English (UK)": [
                            {
                                "tts_voice_id": 3001,
                                "voice_name": "en-GB-SoniaNeural",
                                "provider": "microsoft",
                                "lang": "en-GB",
                            }
                        ]
                    }
                }
            ),
        ])
        client = StudioPromptClient(
            base_url="https://api.prod.uk.five9.net/studio-backend/api/",
            api_key="secret-key",
            scope="ac",
            scope_id="45",
            session=session,
        )

        voices = client.list_tts_voices()

        self.assertEqual(voices[0]["tts_voice_id"], 3001)
        self.assertEqual(voices[0]["voice_name"], "en-GB-SoniaNeural")
        self.assertEqual(voices[0]["language"], "en-GB")
        self.assertEqual(session.calls[1][1], "https://api.prod.uk.five9.net/studio-backend/api/prompt/languages")

    def test_create_prompt_request_matches_studio_payload_shape(self):
        from src.tools.Five9.Prompt_Management.Prompt_Bulk_Upload.studio_prompts import StudioPromptClient

        session = FakeStudioSession([FakeJsonResponse({"prompt_id": 26})])
        client = StudioPromptClient("https://studio.example", "key", "ac", "1", session=session)

        client.create_prompt("Greeting", "Welcome", {"tts_voice_id": 100, "voice_name": "Amanda"})

        _, url, kwargs = session.calls[0]
        self.assertEqual(url, "https://studio.example/api/prompt/prompts")
        self.assertEqual(kwargs["json"]["prompt_name"], "Greeting")
        self.assertEqual(kwargs["json"]["default_tts_value"], "Welcome")
        self.assertEqual(kwargs["json"]["prompt_values"][0]["tts_voice_id"], 100)
        self.assertNotIn("api_key", json.dumps(kwargs["json"]))

    def test_get_prompt_audio_supports_direct_audio_and_download_metadata(self):
        from src.tools.Five9.Prompt_Management.Prompt_Bulk_Upload.studio_prompts import StudioPromptClient

        direct = FakeJsonResponse({}, content=b"RIFFdirect", headers={"Content-Type": "audio/wav"})
        metadata = FakeJsonResponse({"fileName": "a.wav", "fileType": "audio/wav", "path": "/tts/a.wav"})
        download = FakeJsonResponse({}, content=b"RIFFdownload", headers={"Content-Type": "audio/wav"})
        session = FakeStudioSession([direct, metadata, download])
        client = StudioPromptClient("https://studio.example", "key", "ac", "1", session=session)

        direct_audio = client.get_prompt_audio("Hello", 100)
        metadata_audio = client.get_prompt_audio("Hello", 100)
        downloaded = client.download_wav_file(metadata_audio.metadata)

        self.assertEqual(direct_audio.audio_bytes, b"RIFFdirect")
        self.assertEqual(metadata_audio.metadata["path"], "/tts/a.wav")
        self.assertEqual(downloaded, b"RIFFdownload")


class StudioPromptFlowTests(unittest.TestCase):
    def test_flow_skips_existing_by_default_and_redacts_secrets(self):
        from src.tools.Five9.Prompt_Management.Prompt_Bulk_Upload.studio_prompts import (
            StudioPromptClient,
            run_studio_prompt_flow,
        )

        session = FakeStudioSession([
            FakeJsonResponse({"data": [{"prompt_id": 5, "prompt_name": "Greeting"}]}),
        ])
        studio = StudioPromptClient("https://studio.example", "studio-secret", "ac", "1", session=session)
        vcc = FakeVccClient(existing={"Greeting"})

        with tempfile.TemporaryDirectory() as tmp:
            result = run_studio_prompt_flow(
                studio_client=studio,
                vcc_client=vcc,
                prompts=[{"prompt_name": "Greeting", "text": "Hello"}],
                voice={"tts_voice_id": 100, "voice_name": "Amanda"},
                output_dir=tmp,
                approved=True,
                overwrite=False,
            )

        self.assertEqual(result["summary"]["skipped"], 1)
        self.assertEqual(result["results"][0]["action"], "skipped")
        self.assertNotIn("studio-secret", json.dumps(result))
        self.assertFalse(any(call[0] == "add_prompt_wav" for call in vcc.calls))

    def test_flow_creates_studio_prompt_saves_wav_and_uploads_to_vcc(self):
        from src.tools.Five9.Prompt_Management.Prompt_Bulk_Upload.studio_prompts import (
            StudioPromptClient,
            run_studio_prompt_flow,
        )

        session = FakeStudioSession([
            FakeJsonResponse({"data": []}),
            FakeJsonResponse({"prompt_id": 9}),
            FakeJsonResponse({}, content=b"RIFFnew", headers={"Content-Type": "audio/wav"}),
        ])
        studio = StudioPromptClient("https://studio.example", "studio-secret", "ac", "1", session=session)
        vcc = FakeVccClient()

        with tempfile.TemporaryDirectory() as tmp:
            result = run_studio_prompt_flow(
                studio_client=studio,
                vcc_client=vcc,
                prompts=[{"prompt_name": "Greeting", "text": "Hello"}],
                voice={"tts_voice_id": 100, "voice_name": "Amanda"},
                output_dir=tmp,
                approved=True,
            )
            wav_path = Path(result["results"][0]["wav_path"])
            self.assertTrue(wav_path.exists())
            self.assertEqual(wav_path.read_bytes(), b"RIFFnew")

        self.assertEqual(result["summary"]["created"], 1)
        self.assertTrue(any(call[0] == "add_prompt_wav" for call in vcc.calls))

    def test_flow_requires_approval(self):
        from src.tools.Five9.Prompt_Management.Prompt_Bulk_Upload.studio_prompts import run_studio_prompt_flow

        with self.assertRaises(PermissionError):
            run_studio_prompt_flow(
                studio_client=None,
                vcc_client=None,
                prompts=[{"prompt_name": "Greeting", "text": "Hello"}],
                voice={"tts_voice_id": 100, "voice_name": "Amanda"},
                output_dir=".",
                approved=False,
            )


class StudioPromptRouteTests(unittest.TestCase):
    def setUp(self):
        from UI import app as ui_app

        self.ui_app = ui_app

    def test_preview_route_extracts_playbook_prompts(self):
        playbook_bytes = self._prompt_playbook_bytes()

        result = self.ui_app.preview_studio_playbook_prompts(self._upload("prompts.xlsx", playbook_bytes))

        self.assertEqual(result["source"]["file_name"], "prompts.xlsx")
        self.assertGreater(len(result["prompts"]), 0)
        self.assertEqual(result["prompts"][0]["prompt_name"], "Greeting")
        self.assertEqual(result["prompts"][0]["text"], "Thanks for calling.")

    def test_preview_route_rejects_non_xlsx(self):
        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.preview_studio_playbook_prompts(self._upload("notes.txt", b"hello"))

        self.assertEqual(ctx.exception.status_code, 400)

    def test_full_run_requires_approval_and_credentials(self):
        req = self.ui_app.StudioPromptFlowRunRequest(
            approved=False,
            prompts=[{"prompt_name": "Greeting", "text": "Hello"}],
            selected_voice={"tts_voice_id": 100, "voice_name": "Amanda"},
            studio_api_key="",
            studio_scope_id="",
            five9_username="",
            five9_password="",
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.run_studio_prompt_flow_route(req)

        self.assertEqual(ctx.exception.status_code, 403)

    def test_ui_exposes_playbook_studio_flow(self):
        ui_html = (ROOT / "UI" / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("Playbook Studio Flow", ui_html)
        self.assertIn("/api/run/five9/prompt-studio/preview", ui_html)
        self.assertIn("/api/run/five9/prompt-studio/voices", ui_html)
        self.assertIn("/api/run/five9/prompt-studio/audio-probe", ui_html)
        self.assertIn("/api/run/five9/prompt-studio/run", ui_html)
        self.assertIn("STUDIO_SCOPE_ID", ui_html)

    def _upload(self, name: str, data: bytes):
        class FakeUpload:
            filename = name

            def __init__(self, payload: bytes):
                self._file = tempfile.SpooledTemporaryFile()
                self._file.write(payload)
                self._file.seek(0)
                self.file = self._file

        return FakeUpload(data)

    def _prompt_playbook_bytes(self) -> bytes:
        rows = [
            ["Prompt Name", "Prompt Script Verbiage", "Prompt Status"],
            ["Greeting", "Thanks for calling.", ""],
            ["Ignore Me", "Do not use", "ignore"],
        ]
        sheet_rows = []
        for row_index, row in enumerate(rows, start=1):
            cells = []
            for col_index, value in enumerate(row):
                ref = f"{chr(ord('A') + col_index)}{row_index}"
                cells.append(
                    f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>'
                )
            sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
        sheet_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(sheet_rows)}</sheetData>'
            '</worksheet>'
        )
        with tempfile.SpooledTemporaryFile() as file_obj:
            with ZipFile(file_obj, "w") as archive:
                archive.writestr(
                    "[Content_Types].xml",
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                    '<Default Extension="xml" ContentType="application/xml"/>'
                    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                    '</Types>',
                )
                archive.writestr(
                    "_rels/.rels",
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                    '</Relationships>',
                )
                archive.writestr(
                    "xl/workbook.xml",
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                    '<sheets><sheet name="Prompts" sheetId="1" r:id="rId1"/></sheets>'
                    '</workbook>',
                )
                archive.writestr(
                    "xl/_rels/workbook.xml.rels",
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                    '</Relationships>',
                )
                archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
            file_obj.seek(0)
            return file_obj.read()


if __name__ == "__main__":
    unittest.main()
