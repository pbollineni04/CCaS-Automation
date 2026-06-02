import sys
import unittest
from pathlib import Path

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SAMPLE_WRITE_PLAN = [
    {"tool_name": "five9_create_skill", "params": {"name": "English"}},
    {"tool_name": "five9_create_disposition", "params": {"name": "Sale Completed"}},
    {
        "tool_name": "five9_add_prompt_tts",
        "params": {"prompt_name": "Main Greeting", "text": "Thank you for calling."},
    },
    {
        "tool_name": "five9_create_inbound_campaign",
        "params": {
            "campaign_name": "Acme Main Inbound",
            "default_ivr_script_name": "Main IVR",
        },
    },
    {
        "tool_name": "five9_add_dnis_to_campaign",
        "params": {"campaign_name": "Acme Main Inbound", "dnis": ["800-555-0100"]},
    },
    {
        "tool_name": "five9_add_skills_to_campaign",
        "params": {"campaign_name": "Acme Main Inbound", "skills": ["English"]},
    },
    {
        "tool_name": "five9_add_dispositions_to_campaign",
        "params": {"campaign_name": "Acme Main Inbound", "dispositions": ["Sale Completed"]},
    },
    {
        "tool_name": "five9_set_default_ivr_schedule",
        "params": {"campaign_name": "Acme Main Inbound", "script_name": "Main IVR"},
    },
]


class UICoreWriteRouteTests(unittest.TestCase):
    def setUp(self):
        from UI import app as ui_app

        self.ui_app = ui_app

    def test_core_write_route_dry_run_returns_planned_results(self):
        req = self.ui_app.Five9CoreWriteRequest(
            mode="dry_run",
            approved=True,
            planned_calls=SAMPLE_WRITE_PLAN,
        )

        result = self.ui_app.run_five9_core_writes(req)

        self.assertEqual(result["summary"]["mode"], "dry_run")
        self.assertEqual(result["summary"]["total"], 8)
        self.assertTrue(all(item["result"] == "planned" for item in result["results"]))

    def test_core_write_route_live_requires_approval(self):
        req = self.ui_app.Five9CoreWriteRequest(
            mode="live",
            username="user",
            password="pass",
            planned_calls=SAMPLE_WRITE_PLAN,
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.run_five9_core_writes(req)

        self.assertEqual(ctx.exception.status_code, 403)

    def test_core_write_route_rejects_unknown_tool(self):
        req = self.ui_app.Five9CoreWriteRequest(
            mode="dry_run",
            approved=True,
            planned_calls=[{"tool_name": "five9_unknown", "params": {}}],
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.run_five9_core_writes(req)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_home_ui_exposes_core_write_pack(self):
        ui_html = (ROOT / "UI" / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("Core Config Writes", ui_html)
        self.assertIn("five9.core_writes", ui_html)
        self.assertIn("/api/run/five9/core-writes", ui_html)


if __name__ == "__main__":
    unittest.main()
