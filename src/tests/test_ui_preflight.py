import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class UIPreflightRouteTests(unittest.TestCase):
    def setUp(self):
        from UI import app as ui_app

        self.ui_app = ui_app

    def test_stub_preflight_route_returns_read_results(self):
        req = self.ui_app.Five9PreflightRequest(
            mode="stub",
            campaign_dnis_name="Acme Main Inbound",
        )

        result = self.ui_app.run_five9_preflight(req)

        self.assertEqual(result["summary"]["mode"], "stub")
        self.assertEqual(result["summary"]["total"], 6)
        self.assertEqual(result["results"][0]["tool_name"], "five9_get_skills")
        self.assertEqual(result["results"][0]["mode"], "stub")

    def test_empty_campaign_dnis_name_expands_to_all_campaigns(self):
        req = self.ui_app.Five9PreflightRequest(
            mode="stub",
            campaign_dnis_name="",
        )

        result = self.ui_app.run_five9_preflight(req)

        campaign_dnis_reads = [
            read
            for read in result["results"]
            if read["tool_name"] == "five9_get_campaign_dnis_list"
        ]
        campaign_names = [
            read["params"]["campaign_name"]
            for read in campaign_dnis_reads
        ]

        self.assertEqual(campaign_names, ["Acme Main Inbound", "Legacy Billing Inbound"])
        self.assertEqual(result["summary"]["total"], 7)

    def test_empty_campaign_dnis_name_skips_non_inbound_campaigns(self):
        req = self.ui_app.Five9PreflightRequest(
            mode="stub",
            include_skills=False,
            include_dispositions=False,
            include_prompts=False,
            include_dnis=False,
            campaign_dnis_name="",
        )

        campaign_result = {
            "tool_name": "five9_get_campaigns",
            "params": {},
            "timestamp": "2026-05-11T12:00:00",
            "mode": "stub",
            "result": "success",
            "data": [
                {"name": "GenericInbound", "type": "INBOUND"},
                {"name": "GenericOutbound", "type": "OUTBOUND"},
                {"name": "Outbound Campaign", "campaignType": "OUTBOUND"},
            ],
        }

        with patch.object(
            self.ui_app.five9_preflight,
            "five9_get_campaigns",
            return_value=campaign_result,
        ):
            result = self.ui_app.run_five9_preflight(req)

        campaign_dnis_reads = [
            read
            for read in result["results"]
            if read["tool_name"] == "five9_get_campaign_dnis_list"
        ]

        self.assertEqual(len(campaign_dnis_reads), 1)
        self.assertEqual(
            campaign_dnis_reads[0]["params"]["campaign_name"],
            "GenericInbound",
        )

    def test_live_preflight_route_requires_approval(self):
        req = self.ui_app.Five9PreflightRequest(
            mode="live",
            username="user",
            password="pass",
            campaign_dnis_name="Acme Main Inbound",
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.run_five9_preflight(req)

        self.assertEqual(ctx.exception.status_code, 403)

    def test_live_preflight_route_requires_credentials(self):
        req = self.ui_app.Five9PreflightRequest(
            mode="live",
            approved=True,
            campaign_dnis_name="Acme Main Inbound",
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.run_five9_preflight(req)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_preflight_read_failure_returns_failed_result(self):
        req = self.ui_app.Five9PreflightRequest(
            mode="stub",
            include_dispositions=False,
            include_prompts=False,
            include_campaigns=False,
            include_dnis=False,
            include_campaign_dnis=False,
        )

        with patch.object(
            self.ui_app.five9_preflight,
            "five9_get_skills",
            side_effect=RuntimeError("Campaign not found"),
        ):
            result = self.ui_app.run_five9_preflight(req)

        self.assertEqual(result["summary"]["total"], 1)
        self.assertEqual(result["summary"]["failed"], 1)
        self.assertEqual(result["results"][0]["tool_name"], "five9_get_skills")
        self.assertEqual(result["results"][0]["result"], "failed")
        self.assertEqual(result["results"][0]["error"], "Campaign not found")

    def test_preflight_results_table_displays_read_target_context(self):
        ui_html = (ROOT / "UI" / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("formatPreflightContext", ui_html)
        self.assertIn("<th>Target</th>", ui_html)
        self.assertIn("campaign_name", ui_html)


if __name__ == "__main__":
    unittest.main()
