import copy
import sys
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


EXPECTED_GROUPS = {
    "Business Hours",
    "Queues",
    "Skills",
    "Dispositions",
    "Prompts",
    "DNIS / Routing",
    "IVR Intent",
}

EXPECTED_TOOL_ORDER = [
    "five9_create_skill",
    "five9_create_skill",
    "five9_create_skill",
    "five9_create_skill",
    "five9_create_disposition",
    "five9_create_disposition",
    "five9_create_disposition",
    "five9_create_disposition",
    "five9_add_prompt_tts",
    "five9_add_prompt_tts",
    "five9_create_inbound_campaign",
    "five9_add_dnis_to_campaign",
    "five9_add_skills_to_campaign",
    "five9_set_default_ivr_schedule",
]


class DemoFlowTests(unittest.TestCase):
    def test_non_empty_analysis_returns_requirement_groups(self):
        from src.agent import demo_flow

        result = demo_flow.analyze_requirements(demo_flow.DEFAULT_DISCOVERY_TEMPLATE)

        self.assertEqual(set(result["requirements"].keys()), EXPECTED_GROUPS)
        self.assertIn(
            "Set business hours to Monday-Friday, 8:00 AM-6:00 PM Eastern",
            result["requirements"]["Business Hours"],
        )
        self.assertIn("Create Sales queue", result["requirements"]["Queues"])
        self.assertIn(
            "Configure Main IVR options for Sales, Billing, and Support",
            result["requirements"]["IVR Intent"],
        )

    def test_empty_analysis_fails_validation(self):
        from src.agent import demo_flow

        with self.assertRaises(ValueError):
            demo_flow.analyze_requirements("   ")

    def test_planned_calls_match_expected_order(self):
        from src.agent import demo_flow

        result = demo_flow.analyze_requirements(demo_flow.DEFAULT_DISCOVERY_TEMPLATE)
        planned_calls = result["planned_calls"]

        self.assertEqual([call["tool_name"] for call in planned_calls], EXPECTED_TOOL_ORDER)
        self.assertEqual(len(planned_calls), 14)
        self.assertEqual(planned_calls[0]["params"]["name"], "English")
        self.assertEqual(planned_calls[8]["params"]["prompt_name"], "Main Greeting")
        self.assertEqual(planned_calls[13]["params"]["ivr_name"], "Main IVR")

    def test_execution_without_approval_fails(self):
        from src.agent import demo_flow

        planned_calls = demo_flow.analyze_requirements(
            demo_flow.DEFAULT_DISCOVERY_TEMPLATE
        )["planned_calls"]

        with self.assertRaises(PermissionError):
            demo_flow.execute_stub_plan(False, planned_calls)

    def test_mutated_reordered_missing_extra_or_unknown_calls_fail(self):
        from src.agent import demo_flow

        planned_calls = demo_flow.analyze_requirements(
            demo_flow.DEFAULT_DISCOVERY_TEMPLATE
        )["planned_calls"]

        mutated = copy.deepcopy(planned_calls)
        mutated[0]["params"]["name"] = "French"
        with self.assertRaises(ValueError):
            demo_flow.execute_stub_plan(True, mutated)

        reordered = copy.deepcopy(planned_calls)
        reordered[0], reordered[1] = reordered[1], reordered[0]
        with self.assertRaises(ValueError):
            demo_flow.execute_stub_plan(True, reordered)

        missing = copy.deepcopy(planned_calls[:-1])
        with self.assertRaises(ValueError):
            demo_flow.execute_stub_plan(True, missing)

        extra = copy.deepcopy(planned_calls)
        extra.append(copy.deepcopy(planned_calls[0]))
        with self.assertRaises(ValueError):
            demo_flow.execute_stub_plan(True, extra)

        unknown = copy.deepcopy(planned_calls)
        unknown[0]["tool_name"] = "five9_live_delete_everything"
        with self.assertRaises(ValueError):
            demo_flow.execute_stub_plan(True, unknown)

    def test_execution_logs_one_stub_success_per_call(self):
        from src.agent import demo_flow

        planned_calls = demo_flow.analyze_requirements(
            demo_flow.DEFAULT_DISCOVERY_TEMPLATE
        )["planned_calls"]

        logs = demo_flow.execute_stub_plan(True, planned_calls)

        self.assertEqual(len(logs), len(planned_calls))
        for log, call in zip(logs, planned_calls):
            self.assertEqual(log["tool_name"], call["tool_name"])
            self.assertEqual(log["params"], call["params"])
            self.assertEqual(log["mode"], "stub")
            self.assertEqual(log["result"], "success")
            datetime.fromisoformat(log["timestamp"])


try:
    from fastapi.testclient import TestClient
except (ModuleNotFoundError, RuntimeError):
    TestClient = None
    app = None
else:
    from UI.app import app


@unittest.skipIf(TestClient is None, "FastAPI test dependencies are not installed")
class DemoRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_demo_route_serves_html(self):
        response = self.client.get("/demo")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Approval-Gated CCaaS Configuration Agent", response.text)

    def test_analyze_endpoint_rejects_empty_input(self):
        response = self.client.post(
            "/api/demo/analyze-requirements",
            json={"discovery_template": " "},
        )

        self.assertEqual(response.status_code, 400)

    def test_execute_endpoint_rejects_missing_approval(self):
        from src.agent import demo_flow

        planned_calls = demo_flow.analyze_requirements(
            demo_flow.DEFAULT_DISCOVERY_TEMPLATE
        )["planned_calls"]
        response = self.client.post(
            "/api/demo/execute-stubs",
            json={"approved": False, "planned_calls": planned_calls},
        )

        self.assertEqual(response.status_code, 403)

    def test_execute_endpoint_rejects_mutated_calls(self):
        from src.agent import demo_flow

        planned_calls = demo_flow.analyze_requirements(
            demo_flow.DEFAULT_DISCOVERY_TEMPLATE
        )["planned_calls"]
        planned_calls[0]["tool_name"] = "five9_unknown_tool"
        response = self.client.post(
            "/api/demo/execute-stubs",
            json={"approved": True, "planned_calls": planned_calls},
        )

        self.assertEqual(response.status_code, 400)

    def test_execute_endpoint_returns_stub_logs(self):
        from src.agent import demo_flow

        planned_calls = demo_flow.analyze_requirements(
            demo_flow.DEFAULT_DISCOVERY_TEMPLATE
        )["planned_calls"]
        response = self.client.post(
            "/api/demo/execute-stubs",
            json={"approved": True, "planned_calls": planned_calls},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["logs"]), 14)
        self.assertEqual(payload["logs"][0]["mode"], "stub")
        self.assertEqual(
            payload["message"],
            "Stub execution complete. No live Five9 changes were made.",
        )


if __name__ == "__main__":
    unittest.main()
