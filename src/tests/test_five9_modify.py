import importlib
import sys
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeModifyClient:
    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on

    def _record(self, name, params):
        self.calls.append((name, params))
        if self.fail_on == name:
            raise RuntimeError(f"{name} failed")
        return {"modified": name, **params}

    def modify_skill(self, **params):
        return self._record("modify_skill", params)

    def modify_disposition(self, **params):
        return self._record("modify_disposition", params)

    def modify_prompt_tts(self, **params):
        return self._record("modify_prompt_tts", params)

    def modify_inbound_campaign(self, **params):
        return self._record("modify_inbound_campaign", params)


class Five9ModifyToolTests(unittest.TestCase):
    def setUp(self):
        self.modify = importlib.import_module("src.tools.Five9.modify")
        self.modify_skill = importlib.import_module("src.tools.Five9.five9_modify_skill")

    def test_modify_skill_dry_run_returns_planned_result(self):
        result = self.modify_skill.five9_modify_skill(
            skill_name="ZZ_TEST_Codex_DeleteMe",
            description="Updated by Codex",
            mode="dry_run",
        )

        self.assertEqual(result["tool_name"], "five9_modify_skill")
        self.assertEqual(
            result["params"],
            {"skill_name": "ZZ_TEST_Codex_DeleteMe", "description": "Updated by Codex"},
        )
        datetime.fromisoformat(result["timestamp"])
        self.assertEqual(result["mode"], "dry_run")
        self.assertEqual(result["result"], "planned")
        self.assertEqual(result["data"]["would_call"], "modifySkill")

    def test_live_modify_requires_explicit_approval(self):
        with self.assertRaises(PermissionError):
            self.modify_skill.five9_modify_skill(
                skill_name="ZZ_TEST_Codex_DeleteMe",
                mode="live",
                client=FakeModifyClient(),
            )

    def test_live_modify_requires_client(self):
        with self.assertRaises(ValueError):
            self.modify_skill.five9_modify_skill(
                skill_name="ZZ_TEST_Codex_DeleteMe",
                mode="live",
                approved=True,
            )

    def test_live_modify_calls_client_and_logs_success(self):
        client = FakeModifyClient()

        result = self.modify_skill.five9_modify_skill(
            skill_name="ZZ_TEST_Codex_DeleteMe",
            description="Updated by Codex",
            mode="live",
            approved=True,
            client=client,
        )

        self.assertEqual(result["mode"], "live")
        self.assertEqual(result["result"], "success")
        self.assertEqual(
            client.calls,
            [("modify_skill", {"skill_name": "ZZ_TEST_Codex_DeleteMe", "description": "Updated by Codex"})],
        )

    def test_all_modify_tool_names_are_allowed_in_order(self):
        self.assertEqual(
            self.modify.ALLOWED_MODIFY_TOOL_NAMES,
            [
                "five9_modify_skill",
                "five9_modify_disposition",
                "five9_modify_prompt_tts",
                "five9_modify_inbound_campaign",
            ],
        )

    def test_batch_rejects_unknown_tool_name(self):
        with self.assertRaisesRegex(ValueError, "Unknown Five9 modify tool"):
            self.modify.execute_modify_plan(
                approved=True,
                planned_calls=[{"tool_name": "five9_unknown", "params": {}}],
                mode="dry_run",
            )

    def test_live_batch_requires_approval(self):
        with self.assertRaises(PermissionError):
            self.modify.execute_modify_plan(
                approved=False,
                planned_calls=[
                    {"tool_name": "five9_modify_skill", "params": {"skill_name": "ZZ_TEST_Codex_DeleteMe"}}
                ],
                mode="live",
                client=FakeModifyClient(),
            )

    def test_batch_stops_and_logs_failure_if_live_modify_fails(self):
        results = self.modify.execute_modify_plan(
            approved=True,
            planned_calls=[
                {"tool_name": "five9_modify_skill", "params": {"skill_name": "ZZ_TEST_Codex_DeleteMe"}},
                {"tool_name": "five9_modify_disposition", "params": {"name": "Follow Up Required"}},
            ],
            mode="live",
            client=FakeModifyClient(fail_on="modify_skill"),
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["tool_name"], "five9_modify_skill")
        self.assertEqual(results[0]["result"], "failed")
        self.assertIn("modify_skill failed", results[0]["error"])


if __name__ == "__main__":
    unittest.main()
