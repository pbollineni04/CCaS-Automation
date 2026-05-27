import sys
import unittest
from pathlib import Path

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SAMPLE_ROLLBACK_PLAN = [
    {
        "tool_name": "five9_delete_skill",
        "params": {"skill_name": "ZZ_TEST_Codex_DeleteMe"},
    }
]


class UIRollbackRouteTests(unittest.TestCase):
    def setUp(self):
        from UI import app as ui_app

        self.ui_app = ui_app

    def test_rollback_route_dry_run_returns_planned_results(self):
        req = self.ui_app.Five9RollbackRequest(
            mode="dry_run",
            approved=True,
            planned_calls=SAMPLE_ROLLBACK_PLAN,
        )

        result = self.ui_app.run_five9_rollback(req)

        self.assertEqual(result["summary"]["mode"], "dry_run")
        self.assertEqual(result["summary"]["total"], 1)
        self.assertEqual(result["results"][0]["tool_name"], "five9_delete_skill")
        self.assertEqual(result["results"][0]["result"], "planned")

    def test_rollback_route_live_requires_approval(self):
        req = self.ui_app.Five9RollbackRequest(
            mode="live",
            username="user",
            password="pass",
            planned_calls=SAMPLE_ROLLBACK_PLAN,
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.run_five9_rollback(req)

        self.assertEqual(ctx.exception.status_code, 403)

    def test_rollback_route_live_requires_credentials(self):
        req = self.ui_app.Five9RollbackRequest(
            mode="live",
            approved=True,
            planned_calls=SAMPLE_ROLLBACK_PLAN,
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.run_five9_rollback(req)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_rollback_route_rejects_unknown_tool(self):
        req = self.ui_app.Five9RollbackRequest(
            mode="dry_run",
            approved=True,
            planned_calls=[{"tool_name": "five9_unknown", "params": {}}],
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.run_five9_rollback(req)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_home_ui_exposes_rollback_delete_pack(self):
        ui_html = (ROOT / "UI" / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("Rollback Deletes", ui_html)
        self.assertIn("five9.rollback_deletes", ui_html)
        self.assertIn("/api/run/five9/rollback", ui_html)


if __name__ == "__main__":
    unittest.main()
