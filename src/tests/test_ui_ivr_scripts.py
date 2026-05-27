import sys
import unittest
from pathlib import Path

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SAMPLE_IVR_PLAN = [
    {
        "tool_name": "five9_get_ivr_scripts",
        "params": {"name_pattern": "ZZ_TEST_Codex_IVR_Source"},
    },
    {
        "tool_name": "five9_modify_ivr_script",
        "params": {
            "name": "ZZ_TEST_Codex_IVR",
            "description": "Updated IVR",
            "xml_definition": "<ivr-script/>",
        },
    },
]


class UIIvrScriptRouteTests(unittest.TestCase):
    def setUp(self):
        from UI import app as ui_app

        self.ui_app = ui_app

    def test_ivr_script_route_dry_run_returns_results(self):
        req = self.ui_app.Five9IvrScriptRequest(
            mode="dry_run",
            approved=True,
            planned_calls=SAMPLE_IVR_PLAN,
        )

        result = self.ui_app.run_five9_ivr_scripts(req)

        self.assertEqual(result["summary"]["mode"], "dry_run")
        self.assertEqual(result["summary"]["total"], 2)
        self.assertEqual(result["results"][0]["tool_name"], "five9_get_ivr_scripts")
        self.assertEqual(result["results"][0]["result"], "success")
        self.assertEqual(result["results"][1]["result"], "planned")

    def test_ivr_script_route_live_requires_approval(self):
        req = self.ui_app.Five9IvrScriptRequest(
            mode="live",
            username="user",
            password="pass",
            planned_calls=SAMPLE_IVR_PLAN,
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.run_five9_ivr_scripts(req)

        self.assertEqual(ctx.exception.status_code, 403)

    def test_ivr_script_route_live_requires_credentials(self):
        req = self.ui_app.Five9IvrScriptRequest(
            mode="live",
            approved=True,
            planned_calls=SAMPLE_IVR_PLAN,
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.run_five9_ivr_scripts(req)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_ivr_script_route_rejects_unknown_tool(self):
        req = self.ui_app.Five9IvrScriptRequest(
            mode="dry_run",
            approved=True,
            planned_calls=[{"tool_name": "five9_unknown", "params": {}}],
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.run_five9_ivr_scripts(req)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_home_ui_exposes_ivr_script_management_and_xml_discovery(self):
        ui_html = (ROOT / "UI" / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("IVR Scripts", ui_html)
        self.assertIn("IVR Script Management", ui_html)
        self.assertIn("IVR XML Discovery", ui_html)
        self.assertIn("five9.ivr_scripts", ui_html)
        self.assertIn("/api/run/five9/ivr-scripts", ui_html)


if __name__ == "__main__":
    unittest.main()
