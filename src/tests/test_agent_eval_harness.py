import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CASE_PATH = ROOT / "evals" / "cases" / "jacuzzi_playbook_agent_eval.json"


class AgentEvalHarnessTests(unittest.TestCase):
    def test_jacuzzi_case_file_is_loadable(self):
        from evals.agent_eval import load_eval_case

        case = load_eval_case(CASE_PATH)

        self.assertEqual(case["name"], "jacuzzi_playbook_agent")
        self.assertTrue((ROOT / case["playbook_path"]).exists())
        self.assertIn("five9_create_skill", case["expected"]["required_proposed_tools"])
        self.assertIn("five9_modify_ivr_script", case["expected"]["forbidden_proposed_tools"])

    def test_jacuzzi_playbook_agent_eval_passes(self):
        from evals.agent_eval import run_eval_case

        result = run_eval_case(CASE_PATH, repo_root=ROOT)

        self.assertTrue(result["passed"], json.dumps(result["failures"], indent=2))
        self.assertEqual(result["case_name"], "jacuzzi_playbook_agent")
        self.assertGreater(result["metrics"]["proposed_write_calls"], 0)
        self.assertIn("five9_create_ivr_script", result["observed"]["proposed_tools"])
        self.assertEqual(result["failures"], [])

    def test_eval_harness_writes_report(self):
        from evals.agent_eval import run_eval_case

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "report.json"
            result = run_eval_case(CASE_PATH, repo_root=ROOT, report_path=report_path)

            self.assertTrue(result["passed"])
            self.assertTrue(report_path.exists())
            saved = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["case_name"], "jacuzzi_playbook_agent")
            self.assertIn("metrics", saved)

    def test_eval_fails_closed_when_forbidden_tool_is_expected_required(self):
        from evals.agent_eval import run_eval_case

        with tempfile.TemporaryDirectory() as tmpdir:
            bad_case = Path(tmpdir) / "bad_case.json"
            case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
            case["expected"]["required_proposed_tools"].append("five9_modify_ivr_script")
            bad_case.write_text(json.dumps(case), encoding="utf-8")

            result = run_eval_case(bad_case, repo_root=ROOT)

            self.assertFalse(result["passed"])
            self.assertTrue(
                any("Missing required proposed tool" in failure for failure in result["failures"])
            )


if __name__ == "__main__":
    unittest.main()
