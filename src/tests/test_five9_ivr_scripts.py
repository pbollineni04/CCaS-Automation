import importlib
import sys
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeIvrClient:
    def __init__(self, fail_on=None, scripts=None):
        self.calls = []
        self.fail_on = fail_on
        self.scripts = scripts

    def _record(self, name, params):
        self.calls.append((name, params))
        if self.fail_on == name:
            raise RuntimeError(f"{name} failed")
        return {"ivr_operation": name, **params}

    def get_ivr_scripts(self, **params):
        self.calls.append(("get_ivr_scripts", params))
        if self.scripts is not None:
            return self.scripts
        return [
            {
                "name": "ZZ_TEST_Codex_IVR_Source",
                "description": "Source IVR",
                "xmlDefinition": "<ivr-script><module type=\"menu\"/></ivr-script>",
            }
        ]

    def create_ivr_script(self, **params):
        return self._record("create_ivr_script", params)

    def modify_ivr_script(self, **params):
        return self._record("modify_ivr_script", params)

    def delete_ivr_script(self, **params):
        return self._record("delete_ivr_script", params)


class Five9IvrScriptToolTests(unittest.TestCase):
    def setUp(self):
        self.ivr_scripts = importlib.import_module("src.tools.Five9.ivr_scripts")
        self.create_ivr = importlib.import_module("src.tools.Five9.five9_create_ivr_script")
        self.get_ivr = importlib.import_module("src.tools.Five9.five9_get_ivr_scripts")
        self.modify_ivr = importlib.import_module("src.tools.Five9.five9_modify_ivr_script")

    def test_allowed_ivr_tool_names_are_in_order(self):
        self.assertEqual(
            self.ivr_scripts.ALLOWED_IVR_SCRIPT_TOOL_NAMES,
            [
                "five9_get_ivr_scripts",
                "five9_create_ivr_script",
                "five9_modify_ivr_script",
                "five9_delete_ivr_script",
            ],
        )

    def test_dry_run_read_returns_deterministic_script_data_with_xml(self):
        result = self.get_ivr.five9_get_ivr_scripts(
            name_pattern="ZZ_TEST",
            mode="dry_run",
        )

        self.assertEqual(result["tool_name"], "five9_get_ivr_scripts")
        self.assertEqual(result["params"], {"name_pattern": "ZZ_TEST"})
        datetime.fromisoformat(result["timestamp"])
        self.assertEqual(result["mode"], "dry_run")
        self.assertEqual(result["result"], "success")
        self.assertEqual(result["data"][0]["name"], "ZZ_TEST_Codex_IVR_Source")
        self.assertIn("xmlDefinition", result["data"][0])

    def test_dry_run_create_modify_and_delete_return_planned_results(self):
        create_result = self.create_ivr.five9_create_ivr_script(
            name="ZZ_TEST_Codex_IVR",
            mode="dry_run",
        )
        modify_result = self.modify_ivr.five9_modify_ivr_script(
            name="ZZ_TEST_Codex_IVR",
            description="Updated IVR",
            xml_definition="<ivr-script/>",
            mode="dry_run",
        )
        delete_ivr = importlib.import_module("src.tools.Five9.five9_delete_ivr_script")
        delete_result = delete_ivr.five9_delete_ivr_script(
            name="ZZ_TEST_Codex_IVR",
            mode="dry_run",
        )

        self.assertEqual(create_result["result"], "planned")
        self.assertEqual(create_result["data"], {"would_call": "createIVRScript"})
        self.assertEqual(modify_result["result"], "planned")
        self.assertEqual(modify_result["data"], {"would_call": "modifyIVRScript"})
        self.assertEqual(delete_result["result"], "planned")
        self.assertEqual(delete_result["data"], {"would_call": "deleteIVRScript"})

    def test_modify_with_empty_xml_definition_fails_when_xml_key_is_present(self):
        with self.assertRaisesRegex(ValueError, "xml_definition is required"):
            self.modify_ivr.five9_modify_ivr_script(
                name="ZZ_TEST_Codex_IVR",
                xml_definition="   ",
                mode="dry_run",
            )

    def test_live_mode_requires_explicit_approval(self):
        with self.assertRaises(PermissionError):
            self.create_ivr.five9_create_ivr_script(
                name="ZZ_TEST_Codex_IVR",
                mode="live",
                client=FakeIvrClient(),
            )

    def test_live_mode_requires_client(self):
        with self.assertRaises(ValueError):
            self.create_ivr.five9_create_ivr_script(
                name="ZZ_TEST_Codex_IVR",
                mode="live",
                approved=True,
            )

    def test_live_read_calls_client_and_logs_success(self):
        client = FakeIvrClient()

        result = self.get_ivr.five9_get_ivr_scripts(
            name_pattern="ZZ_TEST",
            mode="live",
            approved=True,
            client=client,
        )

        self.assertEqual(result["mode"], "live")
        self.assertEqual(result["result"], "success")
        self.assertEqual(client.calls, [("get_ivr_scripts", {"name_pattern": "ZZ_TEST"})])

    def test_unknown_tool_names_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown Five9 IVR script tool"):
            self.ivr_scripts.execute_ivr_script_plan(
                approved=True,
                planned_calls=[{"tool_name": "five9_unknown", "params": {}}],
                mode="dry_run",
            )

    def test_batch_stops_and_logs_failure_if_live_operation_fails(self):
        results = self.ivr_scripts.execute_ivr_script_plan(
            approved=True,
            planned_calls=[
                {"tool_name": "five9_create_ivr_script", "params": {"name": "ZZ_TEST_Codex_IVR"}},
                {"tool_name": "five9_delete_ivr_script", "params": {"name": "Should Not Run"}},
            ],
            mode="live",
            client=FakeIvrClient(fail_on="create_ivr_script"),
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["tool_name"], "five9_create_ivr_script")
        self.assertEqual(results[0]["result"], "failed")
        self.assertIn("create_ivr_script failed", results[0]["error"])

    def test_upsert_dry_run_reads_creates_missing_script_then_modifies(self):
        results = self.ivr_scripts.execute_ivr_script_upsert(
            approved=False,
            name="ZZ_TEST_New_IVR",
            description="New script",
            xml_definition="<ivrScript/>",
            mode="dry_run",
        )

        self.assertEqual([result["tool_name"] for result in results], [
            "five9_get_ivr_scripts",
            "five9_create_ivr_script",
            "five9_modify_ivr_script",
        ])
        self.assertEqual(results[0]["params"]["name_pattern"], "^ZZ_TEST_New_IVR$")
        self.assertEqual(results[1]["result"], "planned")
        self.assertEqual(results[2]["params"]["xml_definition"], "<ivrScript/>")

    def test_upsert_live_skips_create_when_script_exists(self):
        client = FakeIvrClient(
            scripts=[
                {
                    "name": "ZZ_TEST_Existing_IVR",
                    "xmlDefinition": "<ivrScript/>",
                }
            ]
        )

        results = self.ivr_scripts.execute_ivr_script_upsert(
            approved=True,
            name="ZZ_TEST_Existing_IVR",
            xml_definition="<ivrScript/>",
            mode="live",
            client=client,
        )

        self.assertEqual([call[0] for call in client.calls], ["get_ivr_scripts", "modify_ivr_script"])
        self.assertEqual([result["tool_name"] for result in results], [
            "five9_get_ivr_scripts",
            "five9_modify_ivr_script",
        ])

    def test_upsert_live_creates_missing_script_before_modify(self):
        client = FakeIvrClient(scripts=[])

        results = self.ivr_scripts.execute_ivr_script_upsert(
            approved=True,
            name="ZZ_TEST_New_IVR",
            xml_definition="<ivrScript/>",
            mode="live",
            client=client,
        )

        self.assertEqual([call[0] for call in client.calls], ["get_ivr_scripts", "create_ivr_script", "modify_ivr_script"])
        self.assertEqual([result["tool_name"] for result in results], [
            "five9_get_ivr_scripts",
            "five9_create_ivr_script",
            "five9_modify_ivr_script",
        ])


if __name__ == "__main__":
    unittest.main()
