import sys
import unittest
from pathlib import Path

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SAMPLE_MODIFY_PLAN = [
    {
        "tool_name": "five9_modify_skill",
        "params": {"skill_name": "ZZ_TEST_Codex_DeleteMe", "description": "Updated by Codex"},
    },
    {
        "tool_name": "five9_modify_prompt_tts",
        "params": {"prompt_name": "ZZ_TEST_Codex_Greeting", "text": "Updated greeting."},
    },
]


class UIModifyRouteTests(unittest.TestCase):
    def setUp(self):
        from UI import app as ui_app

        self.ui_app = ui_app

    def test_modify_route_dry_run_returns_planned_results(self):
        req = self.ui_app.Five9ModifyRequest(
            mode="dry_run",
            approved=True,
            planned_calls=SAMPLE_MODIFY_PLAN,
        )

        result = self.ui_app.run_five9_modify(req)

        self.assertEqual(result["summary"]["mode"], "dry_run")
        self.assertEqual(result["summary"]["total"], 2)
        self.assertTrue(all(item["result"] == "planned" for item in result["results"]))

    def test_modify_route_live_requires_approval(self):
        req = self.ui_app.Five9ModifyRequest(
            mode="live",
            username="user",
            password="pass",
            planned_calls=SAMPLE_MODIFY_PLAN,
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.run_five9_modify(req)

        self.assertEqual(ctx.exception.status_code, 403)

    def test_modify_route_live_requires_credentials(self):
        req = self.ui_app.Five9ModifyRequest(
            mode="live",
            approved=True,
            planned_calls=SAMPLE_MODIFY_PLAN,
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.run_five9_modify(req)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_modify_route_rejects_unknown_tool(self):
        req = self.ui_app.Five9ModifyRequest(
            mode="dry_run",
            approved=True,
            planned_calls=[{"tool_name": "five9_unknown", "params": {}}],
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.run_five9_modify(req)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_home_ui_exposes_modify_pack(self):
        ui_html = (ROOT / "UI" / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("Modify Config", ui_html)
        self.assertIn("five9.modify_config", ui_html)
        self.assertIn("/api/run/five9/modify", ui_html)


if __name__ == "__main__":
    unittest.main()
