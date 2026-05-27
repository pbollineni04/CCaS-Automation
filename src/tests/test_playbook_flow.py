import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SAMPLE_PLAYBOOK = (
    ROOT
    / "outputs"
    / "playbook_template_work"
    / "Five9 Voice Implementation Playbook Template - Jacuzzi Fully Converted.xlsx"
)


class PlaybookFlowTests(unittest.TestCase):
    def test_analyze_playbook_extracts_core_five9_entities(self):
        from src.agent import playbook_flow

        result = playbook_flow.analyze_playbook(SAMPLE_PLAYBOOK)

        self.assertEqual(result["source"]["file_name"], SAMPLE_PLAYBOOK.name)
        self.assertIn("Skill", result["source"]["sheets"])
        self.assertIn("Inbound", result["source"]["sheets"])
        self.assertIn("Dispositions", result["requirements"])
        self.assertIn("Main Agent - Tier 1", result["entities"]["skills"])
        self.assertTrue(
            any(
                campaign["campaign_name"] == "JBRx Sales Main Agent Inbound"
                for campaign in result["entities"]["inbound_campaigns"]
            )
        )
        self.assertTrue(
            any(number["number"] == "8008852569-sample" for number in result["entities"]["dnis"])
        )

    def test_agent_plan_creates_preflight_and_core_write_calls_without_ivr_scripts(self):
        from src.agent import playbook_flow

        result = playbook_flow.analyze_playbook(SAMPLE_PLAYBOOK)
        preflight_names = [call["tool_name"] for call in result["preflight_plan"]]
        write_names = [call["tool_name"] for call in result["core_write_plan"]]

        self.assertEqual(
            preflight_names[:5],
            [
                "five9_get_skills",
                "five9_get_dispositions",
                "five9_get_prompts",
                "five9_get_campaigns",
                "five9_get_dnis_list",
            ],
        )
        self.assertIn("five9_create_skill", write_names)
        self.assertIn("five9_create_inbound_campaign", write_names)
        self.assertIn("five9_add_skills_to_campaign", write_names)
        self.assertIn("five9_add_dnis_to_campaign", write_names)
        self.assertNotIn("five9_create_ivr_script", write_names)
        self.assertNotIn("five9_modify_ivr_script", write_names)
        self.assertIn("IVR XML generation deferred", result["deferred"][0])

    def test_structured_skill_cells_use_name_only_for_tool_params(self):
        from src.agent import playbook_flow

        workbook = {
            "Skill": [
                ["Skill Name"],
                ["{'name': 'Rehash', 'type': 'inbound', 'priority': 1}"],
            ],
            "Inbound": [
                ["Campaign Name", "Inbound Skill"],
                ["Rehash Inbound", "{'name': 'Rehash', 'type': 'inbound', 'priority': 1}"],
            ],
        }

        entities = playbook_flow.extract_five9_entities(workbook)
        write_plan = playbook_flow.build_core_write_plan(entities)

        self.assertEqual(entities["skills"], ["Rehash"])
        self.assertEqual(entities["inbound_campaigns"][0]["skills"], ["Rehash"])
        create_skill = next(call for call in write_plan if call["tool_name"] == "five9_create_skill")
        add_skills = next(call for call in write_plan if call["tool_name"] == "five9_add_skills_to_campaign")
        self.assertEqual(create_skill["params"]["name"], "Rehash")
        self.assertNotIn("{", create_skill["params"]["description"])
        self.assertEqual(add_skills["params"]["skills"], ["Rehash"])

    def test_structured_disposition_cells_use_name_only_for_tool_params(self):
        from src.agent import playbook_flow

        workbook = {
            "Dispositions": [
                ["Disposition Name", "Notes"],
                ["{'name': 'Appointment Reset - Rescheduled', 'category': 'appointment'}", ""],
            ],
        }

        entities = playbook_flow.extract_five9_entities(workbook)
        write_plan = playbook_flow.build_core_write_plan(entities)

        self.assertEqual(entities["dispositions"], ["Appointment Reset - Rescheduled"])
        create_disposition = next(
            call for call in write_plan if call["tool_name"] == "five9_create_disposition"
        )
        self.assertEqual(create_disposition["params"]["name"], "Appointment Reset - Rescheduled")

    def test_core_write_plan_defensively_normalizes_structured_names(self):
        from src.agent import playbook_flow

        write_plan = playbook_flow.build_core_write_plan(
            {
                "skills": ["{'name': 'Main Agent - Tier 4', 'description': 'Primary sales agents'}"],
                "dispositions": ["{'name': 'Appointment Reset - Rescheduled', 'category': 'appointment'}"],
                "prompts": [],
                "inbound_campaigns": [],
                "dnis": [],
            }
        )

        self.assertEqual(write_plan[0]["params"]["name"], "Main Agent - Tier 4")
        self.assertEqual(write_plan[0]["params"]["description"], "Skill imported from implementation playbook: Main Agent - Tier 4")
        self.assertEqual(write_plan[1]["params"]["name"], "Appointment Reset - Rescheduled")

    def test_empty_or_missing_playbook_path_fails_validation(self):
        from src.agent import playbook_flow

        with self.assertRaises(ValueError):
            playbook_flow.analyze_playbook("")
        with self.assertRaises(FileNotFoundError):
            playbook_flow.analyze_playbook(ROOT / "missing.xlsx")


class PlaybookRouteTests(unittest.TestCase):
    def setUp(self):
        from UI import app as ui_app

        self.ui_app = ui_app

    def test_playbook_agent_route_returns_downstream_plan(self):
        req = self.ui_app.PlaybookAgentRequest(playbook_path=str(SAMPLE_PLAYBOOK))

        result = self.ui_app.analyze_playbook_agent(req)

        self.assertEqual(result["source"]["file_name"], SAMPLE_PLAYBOOK.name)
        self.assertGreater(result["summary"]["core_write_calls"], 0)
        self.assertFalse(result["summary"]["includes_ivr_scripts"])

    def test_home_ui_exposes_playbook_agent(self):
        ui_html = (ROOT / "UI" / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("Agentic Builder", ui_html)
        self.assertIn("five9.playbook_agent", ui_html)
        self.assertIn("/api/agent/playbook/analyze", ui_html)


if __name__ == "__main__":
    unittest.main()
