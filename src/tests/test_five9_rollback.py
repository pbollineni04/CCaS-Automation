import importlib
import sys
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeRollbackClient:
    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on

    def _record(self, name, params):
        self.calls.append((name, params))
        if self.fail_on == name:
            raise RuntimeError("rollback failed")
        return {"rolled_back": name, **params}

    def delete_skill(self, **params):
        return self._record("delete_skill", params)

    def delete_disposition(self, **params):
        return self._record("delete_disposition", params)

    def delete_prompt(self, **params):
        return self._record("delete_prompt", params)

    def delete_campaign(self, **params):
        return self._record("delete_campaign", params)

    def remove_dnis_from_campaign(self, **params):
        return self._record("remove_dnis_from_campaign", params)

    def remove_skills_from_campaign(self, **params):
        return self._record("remove_skills_from_campaign", params)

    def remove_dispositions_from_campaign(self, **params):
        return self._record("remove_dispositions_from_campaign", params)


class Five9RollbackToolTests(unittest.TestCase):
    def setUp(self):
        self.rollback = importlib.import_module("src.tools.Five9.rollback")
        self.delete_skill = importlib.import_module("src.tools.Five9.five9_delete_skill")

    def test_delete_skill_dry_run_returns_planned_result(self):
        result = self.delete_skill.five9_delete_skill(
            skill_name="ZZ_TEST_Codex_DeleteMe",
            mode="dry_run",
        )

        self.assertEqual(result["tool_name"], "five9_delete_skill")
        self.assertEqual(result["params"], {"skill_name": "ZZ_TEST_Codex_DeleteMe"})
        datetime.fromisoformat(result["timestamp"])
        self.assertEqual(result["mode"], "dry_run")
        self.assertEqual(result["result"], "planned")
        self.assertEqual(result["data"], {"would_call": "deleteSkill"})

    def test_all_rollback_tool_names_are_allowed_in_order(self):
        self.assertEqual(
            self.rollback.ALLOWED_ROLLBACK_TOOL_NAMES,
            [
                "five9_delete_skill",
                "five9_delete_disposition",
                "five9_delete_prompt",
                "five9_delete_campaign",
                "five9_remove_dnis_from_campaign",
                "five9_remove_skills_from_campaign",
                "five9_remove_dispositions_from_campaign",
            ],
        )

    def test_live_rollback_requires_explicit_approval(self):
        with self.assertRaises(PermissionError):
            self.delete_skill.five9_delete_skill(
                skill_name="ZZ_TEST_Codex_DeleteMe",
                mode="live",
                client=FakeRollbackClient(),
            )

    def test_live_rollback_requires_client(self):
        with self.assertRaises(ValueError):
            self.delete_skill.five9_delete_skill(
                skill_name="ZZ_TEST_Codex_DeleteMe",
                mode="live",
                approved=True,
            )

    def test_live_rollback_calls_client_and_logs_success(self):
        client = FakeRollbackClient()

        result = self.delete_skill.five9_delete_skill(
            skill_name="ZZ_TEST_Codex_DeleteMe",
            mode="live",
            approved=True,
            client=client,
        )

        self.assertEqual(result["mode"], "live")
        self.assertEqual(result["result"], "success")
        self.assertEqual(
            client.calls,
            [("delete_skill", {"skill_name": "ZZ_TEST_Codex_DeleteMe"})],
        )

    def test_batch_rejects_unknown_tool_name(self):
        with self.assertRaisesRegex(ValueError, "Unknown Five9 rollback tool"):
            self.rollback.execute_rollback_plan(
                approved=True,
                planned_calls=[{"tool_name": "five9_delete_everything", "params": {}}],
                mode="dry_run",
            )

    def test_batch_stops_and_logs_failure_if_live_rollback_fails(self):
        plan = [
            {"tool_name": "five9_delete_skill", "params": {"skill_name": "ZZ_TEST_Codex_DeleteMe"}},
            {"tool_name": "five9_delete_prompt", "params": {"prompt_name": "Should Not Run"}},
        ]
        client = FakeRollbackClient(fail_on="delete_skill")

        results = self.rollback.execute_rollback_plan(
            approved=True,
            planned_calls=plan,
            mode="live",
            client=client,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["tool_name"], "five9_delete_skill")
        self.assertEqual(results[0]["result"], "failed")
        self.assertEqual(results[0]["error"], "rollback failed")
        self.assertEqual(client.calls, [("delete_skill", {"skill_name": "ZZ_TEST_Codex_DeleteMe"})])


if __name__ == "__main__":
    unittest.main()
