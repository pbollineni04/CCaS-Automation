import importlib
import sys
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeWriteClient:
    def __init__(self):
        self.calls = []

    def create_skill(self, **params):
        self.calls.append(("create_skill", params))
        return {"created": "skill", **params}

    def create_disposition(self, **params):
        self.calls.append(("create_disposition", params))
        return {"created": "disposition", **params}

    def add_prompt_tts(self, **params):
        self.calls.append(("add_prompt_tts", params))
        return {"created": "prompt", **params}

    def create_inbound_campaign(self, **params):
        self.calls.append(("create_inbound_campaign", params))
        return {"created": "campaign", **params}

    def add_dnis_to_campaign(self, **params):
        self.calls.append(("add_dnis_to_campaign", params))
        return {"added": "dnis", **params}

    def add_skills_to_campaign(self, **params):
        self.calls.append(("add_skills_to_campaign", params))
        return {"added": "skills", **params}

    def add_dispositions_to_campaign(self, **params):
        self.calls.append(("add_dispositions_to_campaign", params))
        return {"added": "dispositions", **params}

    def set_default_ivr_schedule(self, **params):
        self.calls.append(("set_default_ivr_schedule", params))
        return {"set": "default_ivr_schedule", **params}


class FailFirstDispositionClient(FakeWriteClient):
    def create_disposition(self, **params):
        self.calls.append(("create_disposition", params))
        if params["name"] == "TEST":
            raise RuntimeError("Five9 rejected TEST")
        return {"created": "disposition", **params}


class Five9CoreWriteToolTests(unittest.TestCase):
    def setUp(self):
        self.core_writes = importlib.import_module("src.tools.Five9.core_writes")
        self.create_skill = importlib.import_module("src.tools.Five9.five9_create_skill")

    def test_dry_run_write_returns_planned_result_without_client(self):
        result = self.create_skill.five9_create_skill(
            name="English",
            description="Language skill",
            mode="dry_run",
        )

        self.assertEqual(result["tool_name"], "five9_create_skill")
        self.assertEqual(result["params"], {"name": "English", "description": "Language skill"})
        datetime.fromisoformat(result["timestamp"])
        self.assertEqual(result["mode"], "dry_run")
        self.assertEqual(result["result"], "planned")
        self.assertEqual(result["data"]["would_call"], "createSkill")

    def test_live_write_requires_explicit_approval(self):
        with self.assertRaises(PermissionError):
            self.create_skill.five9_create_skill(
                name="English",
                mode="live",
                client=FakeWriteClient(),
            )

    def test_live_write_requires_client(self):
        with self.assertRaises(ValueError):
            self.create_skill.five9_create_skill(
                name="English",
                mode="live",
                approved=True,
            )

    def test_live_write_calls_client_and_logs_success(self):
        client = FakeWriteClient()

        result = self.create_skill.five9_create_skill(
            name="English",
            description="Language skill",
            mode="live",
            approved=True,
            client=client,
        )

        self.assertEqual(result["mode"], "live")
        self.assertEqual(result["result"], "success")
        self.assertEqual(client.calls, [("create_skill", {"name": "English", "description": "Language skill"})])

    def test_all_core_write_tool_names_are_allowed_in_order(self):
        self.assertEqual(
            self.core_writes.ALLOWED_CORE_WRITE_TOOL_NAMES,
            [
                "five9_create_skill",
                "five9_create_disposition",
                "five9_add_prompt_tts",
                "five9_create_inbound_campaign",
                "five9_add_dnis_to_campaign",
                "five9_add_skills_to_campaign",
                "five9_add_dispositions_to_campaign",
                "five9_set_default_ivr_schedule",
            ],
        )

    def test_batch_rejects_unknown_tool_name(self):
        with self.assertRaisesRegex(ValueError, "Unknown Five9 core write tool"):
            self.core_writes.execute_core_write_plan(
                approved=True,
                planned_calls=[{"tool_name": "five9_delete_everything", "params": {}}],
                mode="dry_run",
            )

    def test_live_batch_requires_approval(self):
        with self.assertRaises(PermissionError):
            self.core_writes.execute_core_write_plan(
                approved=False,
                planned_calls=[{"tool_name": "five9_create_skill", "params": {"name": "English"}}],
                mode="live",
                client=FakeWriteClient(),
            )

    def test_batch_dry_run_executes_expected_write_plan(self):
        plan = [
            {"tool_name": "five9_create_skill", "params": {"name": "English"}},
            {"tool_name": "five9_create_disposition", "params": {"name": "Sale Completed"}},
            {
                "tool_name": "five9_add_prompt_tts",
                "params": {"prompt_name": "Main Greeting", "text": "Thank you for calling."},
            },
            {
                "tool_name": "five9_create_inbound_campaign",
                "params": {"campaign_name": "Acme Main Inbound"},
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

        results = self.core_writes.execute_core_write_plan(
            approved=True,
            planned_calls=plan,
            mode="dry_run",
        )

        self.assertEqual([result["tool_name"] for result in results], [call["tool_name"] for call in plan])
        self.assertTrue(all(result["mode"] == "dry_run" for result in results))
        self.assertTrue(all(result["result"] == "planned" for result in results))

    def test_live_batch_continues_after_one_write_fails(self):
        client = FailFirstDispositionClient()
        plan = [
            {"tool_name": "five9_create_disposition", "params": {"name": "TEST"}},
            {"tool_name": "five9_create_disposition", "params": {"name": "Customer Hung Up"}},
        ]

        results = self.core_writes.execute_core_write_plan(
            approved=True,
            planned_calls=plan,
            mode="live",
            client=client,
        )

        self.assertEqual([result["result"] for result in results], ["failed", "success"])
        self.assertEqual(
            client.calls,
            [
                ("create_disposition", {"name": "TEST"}),
                ("create_disposition", {"name": "Customer Hung Up"}),
            ],
        )


if __name__ == "__main__":
    unittest.main()
