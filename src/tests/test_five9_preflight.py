import copy
import importlib
import sys
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class Five9PreflightToolTests(unittest.TestCase):
    def setUp(self):
        self.preflight = importlib.import_module("src.tools.Five9.preflight")

    def assert_stub_contract(self, result, expected_tool_name):
        self.assertEqual(result["tool_name"], expected_tool_name)
        self.assertIn("params", result)
        datetime.fromisoformat(result["timestamp"])
        self.assertEqual(result["mode"], "stub")
        self.assertEqual(result["result"], "success")
        self.assertIn("data", result)

    def test_all_preflight_tools_return_stub_contract(self):
        tool_calls = [
            (
                self.preflight.five9_get_skills,
                {},
                "five9_get_skills",
            ),
            (
                self.preflight.five9_get_dispositions,
                {},
                "five9_get_dispositions",
            ),
            (
                self.preflight.five9_get_prompts,
                {},
                "five9_get_prompts",
            ),
            (
                self.preflight.five9_get_campaigns,
                {},
                "five9_get_campaigns",
            ),
            (
                self.preflight.five9_get_dnis_list,
                {},
                "five9_get_dnis_list",
            ),
            (
                self.preflight.five9_get_campaign_dnis_list,
                {"campaign_name": "Acme Main Inbound"},
                "five9_get_campaign_dnis_list",
            ),
        ]

        for func, kwargs, expected_tool_name in tool_calls:
            with self.subTest(tool=expected_tool_name):
                self.assert_stub_contract(func(**kwargs), expected_tool_name)

    def test_read_tools_return_deterministic_data(self):
        skills = self.preflight.five9_get_skills()["data"]
        dispositions = self.preflight.five9_get_dispositions()["data"]
        prompts = self.preflight.five9_get_prompts()["data"]
        campaigns = self.preflight.five9_get_campaigns()["data"]
        dnis = self.preflight.five9_get_dnis_list()["data"]

        self.assertEqual(
            [skill["name"] for skill in skills],
            ["English", "Spanish", "Billing Specialist", "Support"],
        )
        self.assertEqual(
            [disposition["name"] for disposition in dispositions],
            ["Sale Completed", "Billing Resolved", "Transferred to Support"],
        )
        self.assertEqual([prompt["name"] for prompt in prompts], ["Main Greeting"])
        self.assertEqual(
            [campaign["name"] for campaign in campaigns],
            ["Acme Main Inbound", "Legacy Billing Inbound"],
        )
        self.assertEqual(
            [entry["number"] for entry in dnis],
            ["800-555-0100", "800-555-0111", "800-555-0199"],
        )

    def test_name_and_campaign_filters(self):
        skills = self.preflight.five9_get_skills(name_pattern="span")["data"]
        dispositions = self.preflight.five9_get_dispositions(name_pattern="billing")[
            "data"
        ]
        prompts = self.preflight.five9_get_prompts(name_pattern="main")["data"]
        campaigns = self.preflight.five9_get_campaigns(
            name_pattern="legacy", campaign_type="inbound"
        )["data"]
        unassigned_dnis = self.preflight.five9_get_dnis_list(select_unassigned=True)[
            "data"
        ]
        campaign_dnis = self.preflight.five9_get_campaign_dnis_list(
            "Acme Main Inbound"
        )["data"]

        self.assertEqual([skill["name"] for skill in skills], ["Spanish"])
        self.assertEqual(
            [disposition["name"] for disposition in dispositions],
            ["Billing Resolved"],
        )
        self.assertEqual([prompt["name"] for prompt in prompts], ["Main Greeting"])
        self.assertEqual(
            [campaign["name"] for campaign in campaigns],
            ["Legacy Billing Inbound"],
        )
        self.assertEqual(
            [entry["number"] for entry in unassigned_dnis],
            ["800-555-0199"],
        )
        self.assertEqual(
            [entry["number"] for entry in campaign_dnis],
            ["800-555-0100"],
        )

    def test_preflight_does_not_import_live_prompt_client(self):
        for module_name in list(sys.modules):
            if module_name.endswith("five9_prompts"):
                sys.modules.pop(module_name)

        preflight = importlib.import_module("src.tools.Five9.preflight")
        preflight.five9_get_prompts()

        loaded_prompt_clients = [
            module_name
            for module_name in sys.modules
            if module_name.endswith("five9_prompts")
        ]
        self.assertEqual(loaded_prompt_clients, [])


class Five9PreflightComparisonTests(unittest.TestCase):
    def setUp(self):
        self.preflight = importlib.import_module("src.tools.Five9.preflight")

    def _action_for(self, comparison, object_type, name):
        for action in comparison["recommended_action"]:
            if action["object_type"] == object_type and action["name"] == name:
                return action["action"]
        self.fail(f"No recommended action for {object_type} {name}")

    def test_existing_objects_recommend_skip(self):
        desired = {
            "skills": ["English"],
            "dispositions": ["Sale Completed"],
            "prompts": ["Main Greeting"],
            "campaigns": ["Acme Main Inbound"],
            "dnis": [
                {
                    "number": "800-555-0100",
                    "campaign_name": "Acme Main Inbound",
                }
            ],
        }

        comparison = self.preflight.compare_desired_to_preflight(desired)

        self.assertEqual(self._action_for(comparison, "skill", "English"), "skip")
        self.assertEqual(
            self._action_for(comparison, "disposition", "Sale Completed"),
            "skip",
        )
        self.assertEqual(
            self._action_for(comparison, "prompt", "Main Greeting"),
            "skip",
        )
        self.assertEqual(
            self._action_for(comparison, "campaign", "Acme Main Inbound"),
            "skip",
        )
        self.assertEqual(
            self._action_for(comparison, "dnis", "800-555-0100"),
            "skip",
        )
        self.assertEqual(comparison["missing"], {})
        self.assertEqual(comparison["conflicts"], {})

    def test_missing_objects_recommend_create(self):
        desired = {
            "skills": ["Sales Specialist"],
            "dispositions": ["Follow Up Required"],
            "prompts": ["After Hours"],
            "campaigns": ["New Service Inbound"],
            "dnis": [
                {
                    "number": "800-555-0200",
                    "campaign_name": "New Service Inbound",
                }
            ],
        }

        comparison = self.preflight.compare_desired_to_preflight(desired)

        self.assertEqual(
            self._action_for(comparison, "skill", "Sales Specialist"),
            "create",
        )
        self.assertEqual(
            self._action_for(comparison, "disposition", "Follow Up Required"),
            "create",
        )
        self.assertEqual(
            self._action_for(comparison, "prompt", "After Hours"),
            "create",
        )
        self.assertEqual(
            self._action_for(comparison, "campaign", "New Service Inbound"),
            "create",
        )
        self.assertEqual(
            self._action_for(comparison, "dnis", "800-555-0200"),
            "create",
        )

    def test_dnis_assigned_to_another_campaign_recommends_review(self):
        desired = {
            "dnis": [
                {
                    "number": "800-555-0111",
                    "campaign_name": "Acme Main Inbound",
                }
            ]
        }

        comparison = self.preflight.compare_desired_to_preflight(desired)

        self.assertEqual(
            self._action_for(comparison, "dnis", "800-555-0111"),
            "review",
        )
        self.assertEqual(
            comparison["conflicts"]["dnis"],
            [
                {
                    "number": "800-555-0111",
                    "requested_campaign": "Acme Main Inbound",
                    "assigned_campaign": "Legacy Billing Inbound",
                }
            ],
        )

    def test_comparison_does_not_mutate_custom_inventory(self):
        inventory = copy.deepcopy(self.preflight.SAMPLE_FIVE9_INVENTORY)
        original = copy.deepcopy(inventory)

        self.preflight.compare_desired_to_preflight(
            {"skills": ["English", "Sales Specialist"]},
            inventory=inventory,
        )

        self.assertEqual(inventory, original)


if __name__ == "__main__":
    unittest.main()
