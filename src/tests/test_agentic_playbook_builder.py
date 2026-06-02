import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SAMPLE_PLAYBOOK = (
    ROOT
    / "outputs"
    / "playbook_template_work"
    / "Five9 Voice Implementation Playbook Template - Jacuzzi Fully Converted.xlsx"
)


class AgenticPlaybookSchemaTests(unittest.TestCase):
    def test_valid_desired_config_passes_validation(self):
        from src.agent.schemas import validate_desired_config

        desired = {
            "platform": "five9",
            "client_name": "Jacuzzi",
            "skills": ["Main Agent - Tier 1"],
            "dispositions": ["Sale"],
            "prompts": [],
            "inbound_campaigns": [
                {"campaign_name": "JBRx Sales Main Agent Inbound", "skills": ["Main Agent - Tier 1"]}
            ],
            "dnis": [{"number": "8008852569-sample", "campaign_name": "JBRx Sales Main Agent Inbound"}],
            "deferred_items": ["IVR script generation deferred"],
            "rationale": "Parsed from implementation playbook.",
        }

        validated = validate_desired_config(desired)

        self.assertEqual(validated["platform"], "five9")
        self.assertEqual(validated["client_name"], "Jacuzzi")

    def test_missing_client_or_unsupported_platform_fails_validation(self):
        from src.agent.schemas import validate_desired_config

        with self.assertRaises(ValueError):
            validate_desired_config({"platform": "five9", "client_name": ""})
        with self.assertRaises(ValueError):
            validate_desired_config({"platform": "zoom", "client_name": "Acme"})

    def test_ivr_write_requests_fail_validation(self):
        from src.agent.schemas import validate_desired_config

        with self.assertRaises(ValueError):
            validate_desired_config(
                {
                    "platform": "five9",
                    "client_name": "Acme",
                    "skills": [],
                    "dispositions": [],
                    "prompts": [],
                    "inbound_campaigns": [],
                    "dnis": [],
                    "ivr_scripts": [{"name": "Main IVR"}],
                }
            )

    def test_skills_dispositions_and_deferred_items_must_be_clean_strings(self):
        from src.agent.schemas import validate_desired_config

        base = {
            "platform": "five9",
            "client_name": "Jacuzzi",
            "skills": ["Main Agent - Tier 1"],
            "dispositions": ["Appointment Set"],
            "prompts": [],
            "inbound_campaigns": [],
            "dnis": [],
            "deferred_items": ["IVR deferred"],
        }

        self.assertEqual(validate_desired_config(base)["skills"], ["Main Agent - Tier 1"])

        bad_cases = [
            ("skills", [{"name": "Main Agent - Tier 1"}]),
            ("skills", ["{'name': 'Main Agent - Tier 1'}"]),
            ("dispositions", [{"name": "Appointment Set"}]),
            ("dispositions", ['{"name": "Appointment Set"}']),
            ("deferred_items", [{"note": "IVR deferred"}]),
            ("deferred_items", ["['IVR deferred']"]),
        ]
        for field, value in bad_cases:
            invalid = dict(base)
            invalid[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    validate_desired_config(invalid)

    def test_structured_identity_fields_must_be_clean_strings(self):
        from src.agent.schemas import validate_desired_config

        base = {
            "platform": "five9",
            "client_name": "Jacuzzi",
            "skills": [],
            "dispositions": [],
            "prompts": [{"prompt_name": "Main Greeting", "text": "Hello"}],
            "inbound_campaigns": [
                {
                    "campaign_name": "JBRx Sales Main Agent Inbound",
                    "skills": ["Main Agent - Tier 1"],
                    "dispositions": ["Appointment Set"],
                }
            ],
            "dnis": [{"number": "8008852569", "campaign_name": "JBRx Sales Main Agent Inbound"}],
        }

        self.assertEqual(validate_desired_config(base)["client_name"], "Jacuzzi")

        bad_cases = [
            ("prompts", [{"prompt_name": "{'name': 'Main Greeting'}", "text": "Hello"}]),
            ("inbound_campaigns", [{"campaign_name": '{"name":"Bad"}', "skills": []}]),
            ("inbound_campaigns", [{"campaign_name": "Campaign", "skills": [{"name": "Skill"}]}]),
            ("dnis", [{"number": "{'number': '8008852569'}", "campaign_name": "Campaign"}]),
            ("dnis", [{"number": "8008852569", "campaign_name": '{"name":"Campaign"}'}]),
        ]
        for field, value in bad_cases:
            invalid = dict(base)
            invalid[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    validate_desired_config(invalid)

    def test_api_ready_planned_call_contract_accepts_all_core_write_tools(self):
        from src.agent.schemas import ALLOWED_CORE_WRITE_TOOL_NAMES, validate_planned_calls

        planned_calls = [
            {
                "tool_name": "five9_create_skill",
                "params": {
                    "name": "Main Agent - Tier 1",
                    "description": "Primary sales skill",
                    "route_voice_mails": True,
                    "message_of_the_day": "Ready",
                },
            },
            {
                "tool_name": "five9_create_disposition",
                "params": {
                    "name": "Appointment Set",
                    "description": "Booked appointment",
                    "agent_must_complete_worksheet": False,
                    "agent_must_confirm": True,
                    "reset_attempts_counter": False,
                },
            },
            {
                "tool_name": "five9_add_prompt_tts",
                "params": {
                    "prompt_name": "Main Greeting",
                    "text": "Thank you for calling Jacuzzi.",
                    "description": "Main line greeting",
                    "voice": "default",
                    "language": "en-US",
                },
            },
            {
                "tool_name": "five9_create_inbound_campaign",
                "params": {
                    "campaign_name": "JBRx Sales Main Agent Inbound",
                    "default_ivr_script_name": "Main IVR",
                    "description": "Main inbound line",
                    "max_num_of_lines": 10,
                },
            },
            {
                "tool_name": "five9_add_dnis_to_campaign",
                "params": {"campaign_name": "JBRx Sales Main Agent Inbound", "dnis": ["8008852569"]},
            },
            {
                "tool_name": "five9_add_skills_to_campaign",
                "params": {
                    "campaign_name": "JBRx Sales Main Agent Inbound",
                    "skills": ["Main Agent - Tier 1"],
                },
            },
            {
                "tool_name": "five9_add_dispositions_to_campaign",
                "params": {
                    "campaign_name": "JBRx Sales Main Agent Inbound",
                    "dispositions": ["Appointment Set"],
                    "is_skip_preview_disposition": False,
                },
            },
            {
                "tool_name": "five9_set_default_ivr_schedule",
                "params": {
                    "campaign_name": "JBRx Sales Main Agent Inbound",
                    "script_name": "Main IVR",
                    "params": {"timezone": "Eastern"},
                    "is_visual_mode_enabled": True,
                },
            },
        ]

        validated = validate_planned_calls(planned_calls)

        self.assertEqual([call["tool_name"] for call in validated], ALLOWED_CORE_WRITE_TOOL_NAMES)

    def test_api_ready_planned_call_contract_rejects_bad_shapes(self):
        from src.agent.schemas import validate_planned_calls

        bad_cases = [
            [{"tool_name": "five9_delete_skill", "params": {"name": "Bad"}}],
            [{"tool_name": "five9_create_ivr_script", "params": {"name": "Bad"}}],
            [{"tool_name": "five9_create_skill", "params": {"name": "Skill", "unexpected": "x"}}],
            [{"tool_name": "five9_create_skill", "params": {}}],
            [{"tool_name": "five9_create_skill", "params": {"name": ""}}],
            [{"tool_name": "five9_create_skill", "params": {"name": {"name": "Skill"}}}],
            [{"tool_name": "five9_create_skill", "params": {"name": "{'name': 'Skill'}"}}],
            [{"tool_name": "five9_add_skills_to_campaign", "params": {"campaign_name": "Campaign", "skills": [{"name": "Skill"}]}}],
            [{"tool_name": "five9_add_dnis_to_campaign", "params": {"campaign_name": "Campaign", "dnis": "8008852569"}}],
            [{"tool_name": "five9_create_inbound_campaign", "params": {"campaign_name": "Campaign", "default_ivr_script_name": "Main IVR", "max_num_of_lines": "10"}}],
        ]
        for planned_calls in bad_cases:
            with self.subTest(planned_calls=planned_calls):
                with self.assertRaises(ValueError):
                    validate_planned_calls(planned_calls)

    def test_ivr_requirements_validate_as_deferred_planning_only(self):
        from src.agent.schemas import validate_agent_plan_response, validate_ivr_requirements

        ivr_requirements = {
            "script_name": "Main IVR",
            "intent": "Route callers by menu option",
            "business_hours": "Monday-Friday 8:00 AM-6:00 PM Eastern",
            "greetings": ["Main Greeting", "After Hours"],
            "menu_options": [
                {"digit": "1", "label": "Sales", "target": "Sales"},
                {"digit": "2", "label": "Billing", "target": "Billing"},
            ],
            "routing_targets": ["Sales", "Billing"],
            "notes": ["Build script XML later from approved IVR builder."],
        }

        validated = validate_ivr_requirements(ivr_requirements)
        self.assertEqual(validated["script_name"], "Main IVR")
        self.assertEqual(validated["menu_options"][0]["digit"], "1")

        agent_plan = validate_agent_plan_response(
            {
                "client_name": "Jacuzzi",
                "planned_calls": [{"tool_name": "five9_create_skill", "params": {"name": "Sales"}}],
                "ivr_requirements": ivr_requirements,
                "ivr_script_plan": [
                    {"tool_name": "five9_create_ivr_script", "params": {"name": "Main IVR"}}
                ],
                "deferred_items": ["IVR script generation deferred"],
                "rationale": "Mock response",
            }
        )
        self.assertEqual(agent_plan["ivr_requirements"]["script_name"], "Main IVR")
        self.assertEqual(agent_plan["ivr_script_plan"][0]["tool_name"], "five9_create_ivr_script")

    def test_ivr_requirements_reject_xml_and_malformed_shapes(self):
        from src.agent.schemas import validate_agent_plan_response, validate_ivr_requirements

        bad_requirements = [
            {"script_name": "Main IVR", "intent": "x", "business_hours": "", "greetings": [], "menu_options": [], "routing_targets": [], "notes": [], "xmlDefinition": "<ivrScript/>"},
            {"script_name": "Main IVR", "intent": "<ivrScript></ivrScript>", "business_hours": "", "greetings": [], "menu_options": [], "routing_targets": [], "notes": []},
            {"script_name": "Main IVR", "intent": "x", "business_hours": "", "greetings": [{"name": "Prompt"}], "menu_options": [], "routing_targets": [], "notes": []},
            {"script_name": "Main IVR", "intent": "x", "business_hours": "", "greetings": [], "menu_options": [{"digit": 1, "label": "Sales", "target": "Sales"}], "routing_targets": [], "notes": []},
            {"script_name": "Main IVR", "intent": "x", "business_hours": "", "greetings": [], "menu_options": [], "routing_targets": [], "notes": [{"note": "bad"}]},
        ]
        for ivr_requirements in bad_requirements:
            with self.subTest(ivr_requirements=ivr_requirements):
                with self.assertRaises(ValueError):
                    validate_ivr_requirements(ivr_requirements)

        with self.assertRaises(ValueError):
            validate_agent_plan_response(
                {
                    "client_name": "Jacuzzi",
                    "planned_calls": [
                        {"tool_name": "five9_create_ivr_script", "params": {"name": "Main IVR"}}
                    ],
                    "ivr_requirements": {
                        "script_name": "Main IVR",
                        "intent": "Build IVR",
                        "business_hours": "",
                        "greetings": [],
                        "menu_options": [],
                        "routing_targets": [],
                        "notes": [],
                    },
                    "deferred_items": [],
                    "rationale": "bad",
                }
            )

        for tool_name in ("five9_modify_ivr_script", "five9_delete_ivr_script"):
            with self.subTest(tool_name=tool_name):
                with self.assertRaises(ValueError):
                    validate_agent_plan_response(
                        {
                            "client_name": "Jacuzzi",
                            "planned_calls": [],
                            "ivr_requirements": {},
                            "ivr_script_plan": [{"tool_name": tool_name, "params": {"name": "Main IVR"}}],
                            "deferred_items": [],
                            "rationale": "bad",
                        }
                    )


class ClaudeClientTests(unittest.TestCase):
    def test_system_prompt_contains_required_output_contract(self):
        from src.agent.claude_client import _system_prompt

        prompt = _system_prompt()

        self.assertIn("Required Output JSON", prompt)
        self.assertIn("Do not return markdown", prompt)
        self.assertIn("Do not wrap JSON in prose", prompt)
        self.assertIn("Do not include extra keys", prompt)
        self.assertIn("planned_calls", prompt)
        self.assertIn("ivr_requirements", prompt)
        self.assertIn("ivr_script_plan", prompt)
        self.assertIn("menu_options", prompt)
        self.assertIn("No IVR XML", prompt)
        self.assertIn("five9_create_skill", prompt)
        self.assertIn("five9_create_disposition", prompt)
        self.assertIn("five9_add_prompt_tts", prompt)
        self.assertIn("five9_create_inbound_campaign", prompt)
        self.assertIn("five9_add_dnis_to_campaign", prompt)
        self.assertIn("five9_add_skills_to_campaign", prompt)
        self.assertIn("five9_add_dispositions_to_campaign", prompt)
        self.assertIn("five9_set_default_ivr_schedule", prompt)
        self.assertIn("Forbidden shapes", prompt)
        self.assertIn("five9_delete_skill", prompt)
        self.assertIn("five9_create_ivr_script", prompt)
        self.assertIn("five9_modify_ivr_script", prompt)
        self.assertIn("five9_delete_ivr_script", prompt)
        self.assertIn("xmlDefinition", prompt)
        self.assertIn('"skills": [{"name": "Skill"}]', prompt)
        self.assertIn("will be rejected", prompt)
        self.assertIn("Do not output raw SOAP XML", prompt)
        self.assertIn("Do not execute tools", prompt)
        self.assertNotIn("You may execute", prompt)

    def test_missing_api_key_uses_fallback_mode(self):
        from src.agent.claude_client import interpret_playbook_with_claude
        from src.agent.playbook_parser import parse_playbook

        previous = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            parsed = parse_playbook(SAMPLE_PLAYBOOK)
            result = interpret_playbook_with_claude(parsed)
        finally:
            if previous is not None:
                os.environ["ANTHROPIC_API_KEY"] = previous

        self.assertEqual(result["ai_mode"], "fallback")
        self.assertIn("agent_plan", result)
        self.assertGreater(len(result["planned_calls"]), 0)
        self.assertTrue(all(call["tool_name"].startswith("five9_") for call in result["planned_calls"]))

    def test_mocked_claude_response_is_validated(self):
        from src.agent.claude_client import interpret_playbook_with_claude
        from src.agent.playbook_parser import parse_playbook

        class FakeSession:
            def post(self, *args, **kwargs):
                class Response:
                    def raise_for_status(self):
                        return None

                    def json(self):
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(
                                        {
                                            "client_name": "Claude Client",
                                            "planned_calls": [
                                                {
                                                    "tool_name": "five9_create_skill",
                                                    "params": {
                                                        "name": "Claude Skill",
                                                        "description": "Mock skill",
                                                    },
                                                }
                                            ],
                                            "ivr_requirements": {
                                                "script_name": "Main IVR",
                                                "intent": "Route callers by menu option",
                                                "business_hours": "",
                                                "greetings": ["Main Greeting"],
                                                "menu_options": [
                                                    {"digit": "1", "label": "Sales", "target": "Claude Skill"}
                                                ],
                                                "routing_targets": ["Claude Skill"],
                                                "notes": ["XML generation deferred"],
                                            },
                                            "ivr_script_plan": [
                                                {"tool_name": "five9_create_ivr_script", "params": {"name": "Main IVR"}}
                                            ],
                                            "deferred_items": ["IVR script generation deferred"],
                                            "rationale": "Mock response",
                                        }
                                    ),
                                }
                            ]
                        }

                return Response()

        parsed = parse_playbook(SAMPLE_PLAYBOOK)
        result = interpret_playbook_with_claude(
            parsed,
            api_key="test-key",
            session=FakeSession(),
        )

        self.assertEqual(result["ai_mode"], "claude")
        self.assertEqual(result["agent_plan"]["client_name"], "Claude Client")
        self.assertEqual(result["agent_plan"]["ivr_requirements"]["script_name"], "Main IVR")
        self.assertEqual(result["planned_calls"][0]["tool_name"], "five9_create_skill")
        self.assertEqual(result["planned_calls"][0]["params"]["name"], "Claude Skill")

    def test_mocked_openai_response_is_validated(self):
        from src.agent.claude_client import interpret_playbook_with_llm
        from src.agent.playbook_parser import parse_playbook

        class FakeSession:
            def post(self, *args, **kwargs):
                class Response:
                    def raise_for_status(self):
                        return None

                    def json(self):
                        return {
                            "output_text": json.dumps(
                                {
                                    "client_name": "OpenAI Client",
                                    "planned_calls": [
                                        {
                                            "tool_name": "five9_create_skill",
                                            "params": {"name": "OpenAI Skill"},
                                        }
                                    ],
                                    "ivr_requirements": {
                                        "script_name": "Main IVR",
                                        "intent": "Route callers by menu option",
                                        "business_hours": "",
                                        "greetings": ["Main Greeting"],
                                        "menu_options": [
                                            {"digit": "1", "label": "Sales", "target": "OpenAI Skill"}
                                        ],
                                        "routing_targets": ["OpenAI Skill"],
                                        "notes": ["XML generation deferred"],
                                    },
                                    "ivr_script_plan": [
                                        {"tool_name": "five9_create_ivr_script", "params": {"name": "Main IVR"}}
                                    ],
                                    "deferred_items": ["IVR script generation deferred"],
                                    "rationale": "Mock response",
                                }
                            )
                        }

                return Response()

        parsed = parse_playbook(SAMPLE_PLAYBOOK)
        result = interpret_playbook_with_llm(
            parsed,
            provider="openai",
            api_key="test-key",
            model="gpt-test",
            session=FakeSession(),
        )

        self.assertEqual(result["ai_mode"], "openai")
        self.assertEqual(result["agent_plan"]["client_name"], "OpenAI Client")
        self.assertEqual(result["agent_plan"]["ivr_requirements"]["menu_options"][0]["digit"], "1")
        self.assertEqual(result["planned_calls"][0]["params"]["name"], "OpenAI Skill")

    def test_mocked_claude_object_skills_fall_back_with_review_item(self):
        from src.agent.claude_client import interpret_playbook_with_claude
        from src.agent.playbook_parser import parse_playbook

        class FakeSession:
            def post(self, *args, **kwargs):
                class Response:
                    def raise_for_status(self):
                        return None

                    def json(self):
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(
                                        {
                                            "client_name": "Claude Client",
                                            "planned_calls": [
                                                {
                                                    "tool_name": "five9_create_skill",
                                                    "params": {
                                                        "name": {
                                                            "name": "Main Agent - Tier 1",
                                                            "description": "Bad object shape",
                                                        }
                                                    },
                                                }
                                            ],
                                            "ivr_requirements": {
                                                "script_name": "Main IVR",
                                                "intent": "Route callers",
                                                "business_hours": "",
                                                "greetings": [],
                                                "menu_options": [],
                                                "routing_targets": [],
                                                "notes": [],
                                            },
                                            "ivr_script_plan": [],
                                            "deferred_items": ["IVR deferred"],
                                            "rationale": "Mock response",
                                        }
                                    ),
                                }
                            ]
                        }

                return Response()

        parsed = parse_playbook(SAMPLE_PLAYBOOK)
        result = interpret_playbook_with_claude(
            parsed,
            api_key="test-key",
            session=FakeSession(),
        )

        self.assertEqual(result["ai_mode"], "fallback")
        self.assertTrue(
            any("planned_calls[0].params.name" in item["message"] for item in result["review_items"])
        )
        self.assertNotIn("{'name'", json.dumps(result["agent_plan"]))

    def test_mocked_gemini_response_is_validated(self):
        from src.agent.claude_client import interpret_playbook_with_llm
        from src.agent.playbook_parser import parse_playbook

        class FakeSession:
            def post(self, *args, **kwargs):
                class Response:
                    def raise_for_status(self):
                        return None

                    def json(self):
                        return {
                            "candidates": [
                                {
                                    "content": {
                                        "parts": [
                                            {
                                                "text": json.dumps(
                                                    {
                                                        "client_name": "Gemini Client",
                                                        "planned_calls": [
                                                            {
                                                                "tool_name": "five9_create_skill",
                                                                "params": {"name": "Gemini Skill"},
                                                            }
                                                        ],
                                                        "ivr_requirements": {
                                                            "script_name": "Main IVR",
                                                            "intent": "Route callers by menu option",
                                                            "business_hours": "",
                                                            "greetings": ["Main Greeting"],
                                                            "menu_options": [
                                                                {"digit": "1", "label": "Sales", "target": "Gemini Skill"}
                                                            ],
                                                            "routing_targets": ["Gemini Skill"],
                                                            "notes": ["XML generation deferred"],
                                                        },
                                                        "ivr_script_plan": [
                                                            {"tool_name": "five9_create_ivr_script", "params": {"name": "Main IVR"}}
                                                        ],
                                                        "deferred_items": ["IVR script generation deferred"],
                                                        "rationale": "Mock response",
                                                    }
                                                )
                                            }
                                        ]
                                    }
                                }
                            ]
                        }

                return Response()

        parsed = parse_playbook(SAMPLE_PLAYBOOK)
        result = interpret_playbook_with_llm(
            parsed,
            provider="gemini",
            api_key="test-key",
            model="gemini-test",
            session=FakeSession(),
        )

        self.assertEqual(result["ai_mode"], "gemini")
        self.assertEqual(result["agent_plan"]["client_name"], "Gemini Client")
        self.assertEqual(result["agent_plan"]["ivr_requirements"]["routing_targets"], ["Gemini Skill"])
        self.assertEqual(result["planned_calls"][0]["params"]["name"], "Gemini Skill")

    def test_mocked_ivr_xml_response_falls_back_with_review_item(self):
        from src.agent.claude_client import interpret_playbook_with_claude
        from src.agent.playbook_parser import parse_playbook

        class FakeSession:
            def post(self, *args, **kwargs):
                class Response:
                    def raise_for_status(self):
                        return None

                    def json(self):
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(
                                        {
                                            "client_name": "Claude Client",
                                            "planned_calls": [],
                                            "ivr_requirements": {
                                                "script_name": "Main IVR",
                                                "intent": "Build IVR",
                                                "business_hours": "",
                                                "greetings": [],
                                                "menu_options": [],
                                                "routing_targets": [],
                                                "notes": [],
                                                "xmlDefinition": "<ivrScript/>",
                                            },
                                            "ivr_script_plan": [],
                                            "deferred_items": [],
                                            "rationale": "Bad response",
                                        }
                                    ),
                                }
                            ]
                        }

                return Response()

        parsed = parse_playbook(SAMPLE_PLAYBOOK)
        result = interpret_playbook_with_claude(parsed, api_key="test-key", session=FakeSession())

        self.assertEqual(result["ai_mode"], "fallback")
        self.assertTrue(any("ivr_requirements" in item["message"] for item in result["review_items"]))

    def test_provider_failure_redacts_api_keys_from_review_items(self):
        import requests

        from src.agent.claude_client import interpret_playbook_with_llm
        from src.agent.playbook_parser import parse_playbook

        class FakeSession:
            def post(self, *args, **kwargs):
                class Response:
                    def raise_for_status(self):
                        raise requests.HTTPError(
                            "429 Client Error: Too Many Requests for url: "
                            "https://generativelanguage.googleapis.com/v1beta/models/"
                            "gemini-2.5-pro:generateContent?key=SECRET_TEST_KEY"
                        )

                    def json(self):
                        return {}

                return Response()

        parsed = parse_playbook(SAMPLE_PLAYBOOK)
        result = interpret_playbook_with_llm(
            parsed,
            provider="gemini",
            api_key="SECRET_TEST_KEY",
            session=FakeSession(),
        )
        message = result["review_items"][0]["message"]

        self.assertEqual(result["ai_mode"], "fallback")
        self.assertIn("429 Client Error", message)
        self.assertNotIn("SECRET_TEST_KEY", message)
        self.assertIn("key=[redacted]", message)

    def test_malformed_claude_response_falls_back_with_review_item(self):
        from src.agent.claude_client import interpret_playbook_with_claude
        from src.agent.playbook_parser import parse_playbook

        class FakeSession:
            def post(self, *args, **kwargs):
                class Response:
                    def raise_for_status(self):
                        return None

                    def json(self):
                        return {"content": [{"type": "text", "text": "not json"}]}

                return Response()

        parsed = parse_playbook(SAMPLE_PLAYBOOK)
        result = interpret_playbook_with_claude(
            parsed,
            api_key="test-key",
            session=FakeSession(),
        )

        self.assertEqual(result["ai_mode"], "fallback")
        self.assertTrue(any("Claude interpretation failed" in item["message"] for item in result["review_items"]))


class AgenticGraphTests(unittest.TestCase):
    def test_agent_preflight_plan_does_not_read_dnis_from_future_campaigns(self):
        from src.agent.planner import build_agent_preflight_plan

        planned_calls = [
            {
                "tool_name": "five9_create_inbound_campaign",
                "params": {
                    "campaign_name": "JBRx Sales Main Agent Inbound",
                    "default_ivr_script_name": "Main IVR",
                },
            },
            {
                "tool_name": "five9_add_dnis_to_campaign",
                "params": {
                    "campaign_name": "JBRx Sales Main Agent Inbound",
                    "dnis": ["8008852569"],
                },
            },
        ]

        preflight_plan = build_agent_preflight_plan(planned_calls)

        self.assertEqual(
            [call["tool_name"] for call in preflight_plan],
            [
                "five9_get_skills",
                "five9_get_dispositions",
                "five9_get_prompts",
                "five9_get_campaigns",
                "five9_get_dnis_list",
            ],
        )

    def test_graph_runs_playbook_to_approval_ready_plan(self):
        from src.agent.schemas import ALLOWED_CORE_WRITE_TOOL_NAMES, ALLOWED_PLAYBOOK_IVR_SCRIPT_TOOL_NAMES
        from src.agent.graph import run_playbook_agent

        result = run_playbook_agent(SAMPLE_PLAYBOOK)

        self.assertIn(result["ai_mode"], {"fallback", "claude"})
        self.assertIn("agent_plan", result)
        self.assertIn("ai_planned_calls", result)
        self.assertIn("ivr_requirements", result)
        self.assertIn("ivr_preflight_plan", result)
        self.assertIn("proposed_ivr_script_plan", result)
        self.assertGreater(len(result["ai_planned_calls"]), 0)
        self.assertGreater(len(result["preflight_plan"]), 0)
        self.assertIn("comparison", result)
        self.assertGreater(len(result["proposed_write_plan"]), 0)
        allowed_agent_write_tools = set(ALLOWED_CORE_WRITE_TOOL_NAMES) | set(ALLOWED_PLAYBOOK_IVR_SCRIPT_TOOL_NAMES)
        self.assertTrue(
            all(call["tool_name"] in allowed_agent_write_tools for call in result["proposed_write_plan"])
        )
        self.assertTrue(any(call["tool_name"] == "five9_create_ivr_script" for call in result["proposed_write_plan"]))
        self.assertEqual(result["proposed_write_plan"][0]["tool_name"], "five9_create_ivr_script")
        campaign_creates = [
            call
            for call in result["proposed_write_plan"]
            if call["tool_name"] == "five9_create_inbound_campaign"
        ]
        self.assertTrue(campaign_creates)
        self.assertTrue(
            all(call["params"]["default_ivr_script_name"] == "Main Inbound" for call in campaign_creates)
        )
        self.assertFalse(any(call["tool_name"] == "five9_modify_ivr_script" for call in result["proposed_write_plan"]))
        self.assertFalse(any(call["tool_name"] == "five9_delete_ivr_script" for call in result["proposed_write_plan"]))
        self.assertTrue(all(call["tool_name"] == "five9_get_ivr_scripts" for call in result["ivr_preflight_plan"]))
        self.assertTrue(any("IVR XML generation deferred" in item for item in result["deferred_items"]))
        self.assertTrue(result["plan_id"])

    def test_graph_can_compare_against_live_preflight_results(self):
        from src.agent.graph import run_playbook_agent

        class FakeLivePreflightClient:
            def get_skills(self, name_pattern=None):
                return [{"name": "Jacuzzi Existing Skill"}]

            def get_dispositions(self, name_pattern=None):
                return []

            def get_prompts(self):
                return []

            def get_campaigns(self, name_pattern=None, campaign_type=None):
                return []

            def get_dnis_list(self, select_unassigned=False):
                return []

            def get_campaign_dnis_list(self, campaign_name):
                return []

        class FakeSession:
            def post(self, *args, **kwargs):
                class Response:
                    def raise_for_status(self):
                        return None

                    def json(self):
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(
                                        {
                                            "client_name": "Jacuzzi",
                                            "planned_calls": [
                                                {
                                                    "tool_name": "five9_create_skill",
                                                    "params": {"name": "Jacuzzi Existing Skill"},
                                                },
                                                {
                                                    "tool_name": "five9_create_skill",
                                                    "params": {"name": "Jacuzzi Missing Skill"},
                                                },
                                            ],
                                            "ivr_requirements": {},
                                            "ivr_script_plan": [],
                                            "deferred_items": [],
                                            "rationale": "Mock response",
                                        }
                                    ),
                                }
                            ]
                        }

                return Response()

        result = run_playbook_agent(
            SAMPLE_PLAYBOOK,
            api_key="test-key",
            session=FakeSession(),
            preflight_mode="live",
            preflight_approved=True,
            preflight_client=FakeLivePreflightClient(),
        )

        self.assertEqual(result["preflight_mode"], "live")
        self.assertTrue(result["preflight_live"])
        self.assertTrue(all(item["mode"] == "live" for item in result["preflight_results"]))
        self.assertIn("Jacuzzi Existing Skill", result["comparison"]["exists"]["skills"])
        self.assertIn("Jacuzzi Missing Skill", result["comparison"]["missing"]["skills"])
        self.assertEqual(
            result["proposed_write_plan"],
            [{"tool_name": "five9_create_skill", "params": {"name": "Jacuzzi Missing Skill"}}],
        )

    def test_write_plan_excludes_existing_and_review_items(self):
        from src.agent.graph import run_playbook_agent

        result = run_playbook_agent(SAMPLE_PLAYBOOK)
        write_targets = {
            json.dumps(call["params"], sort_keys=True)
            for call in result["proposed_write_plan"]
        }

        self.assertFalse(any("English" in target for target in write_targets))
        self.assertTrue(all(action["action"] != "review" for action in result["write_actions"]))

    def test_write_plan_excludes_dnis_call_when_any_number_conflicts(self):
        from src.agent.planner import build_agent_write_plan

        planned_calls = [
            {
                "tool_name": "five9_add_dnis_to_campaign",
                "params": {
                    "campaign_name": "New Campaign",
                    "dnis": ["8001111111", "8002222222"],
                },
            }
        ]
        comparison = {
            "missing": {"dnis": [{"number": "8001111111", "campaign_name": "New Campaign"}]},
            "conflicts": {
                "dnis": [
                    {
                        "number": "8002222222",
                        "assigned_campaign": "Existing Campaign",
                        "requested_campaign": "New Campaign",
                    }
                ]
            },
            "recommended_action": [],
        }

        write_plan, _, review_items = build_agent_write_plan(planned_calls, comparison)

        self.assertEqual(write_plan, [])
        self.assertTrue(any("8002222222" in item["message"] for item in review_items))

    def test_write_plan_rejects_stringified_object_params(self):
        from src.agent.planner import build_agent_write_plan

        planned_calls = [
            {
                "tool_name": "five9_create_skill",
                "params": {"name": "{'name': 'Main Agent - Tier 1'}"},
            }
        ]
        comparison = {
            "missing": {"skills": ["{'name': 'Main Agent - Tier 1'}"]},
            "conflicts": {},
            "recommended_action": [],
        }

        with self.assertRaises(ValueError):
            build_agent_write_plan(planned_calls, comparison)


class AgenticRouteTests(unittest.TestCase):
    def setUp(self):
        from UI import app as ui_app

        self.ui_app = ui_app

    def test_upload_route_rejects_non_xlsx(self):
        upload = self._upload("notes.txt", b"hello")

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.analyze_playbook_upload(upload)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_upload_route_returns_agent_plan(self):
        upload = self._upload(SAMPLE_PLAYBOOK.name, SAMPLE_PLAYBOOK.read_bytes())

        result = self.ui_app.analyze_playbook_upload(upload)

        self.assertIn(result["ai_mode"], {"fallback", "claude"})
        self.assertTrue(result["plan_id"])
        self.assertIn("ai_planned_calls", result)
        self.assertIn("ivr_requirements", result)
        self.assertIn("ivr_preflight_plan", result)
        self.assertIn("proposed_ivr_script_plan", result)
        self.assertGreater(len(result["proposed_write_plan"]), 0)
        self.assertIn("comparison", result)

    def test_upload_route_accepts_ai_provider_fields(self):
        upload = self._upload(SAMPLE_PLAYBOOK.name, SAMPLE_PLAYBOOK.read_bytes())

        result = self.ui_app.analyze_playbook_upload(
            upload,
            ai_provider="anthropic",
            api_key="",
            model="",
            ai_required=False,
        )

        self.assertIn(result["ai_mode"], {"fallback", "claude"})
        self.assertTrue(result["plan_id"])

    def test_upload_route_live_preflight_requires_approval_and_credentials(self):
        upload = self._upload(SAMPLE_PLAYBOOK.name, SAMPLE_PLAYBOOK.read_bytes())

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.analyze_playbook_upload(
                upload,
                preflight_mode="live",
                preflight_approved=False,
                preflight_username="user",
                preflight_password="pass",
            )

        self.assertEqual(ctx.exception.status_code, 403)

        upload = self._upload(SAMPLE_PLAYBOOK.name, SAMPLE_PLAYBOOK.read_bytes())
        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.analyze_playbook_upload(
                upload,
                preflight_mode="live",
                preflight_approved=True,
                preflight_username="",
                preflight_password="",
            )

        self.assertEqual(ctx.exception.status_code, 400)

    def test_upload_route_live_preflight_uses_five9_client(self):
        upload = self._upload(SAMPLE_PLAYBOOK.name, SAMPLE_PLAYBOOK.read_bytes())
        original_client = self.ui_app.Five9ConfigClient

        class FakeLivePreflightClient:
            def __init__(self, username, password, domain):
                self.username = username
                self.password = password
                self.domain = domain

            def get_skills(self, name_pattern=None):
                return []

            def get_dispositions(self, name_pattern=None):
                return []

            def get_prompts(self):
                return []

            def get_campaigns(self, name_pattern=None, campaign_type=None):
                return []

            def get_dnis_list(self, select_unassigned=False):
                return []

            def get_campaign_dnis_list(self, campaign_name):
                return []

        try:
            self.ui_app.Five9ConfigClient = FakeLivePreflightClient
            result = self.ui_app.analyze_playbook_upload(
                upload,
                preflight_mode="live",
                preflight_approved=True,
                preflight_domain="api.five9.com",
                preflight_username="user",
                preflight_password="pass",
            )
        finally:
            self.ui_app.Five9ConfigClient = original_client

        self.assertEqual(result["preflight_mode"], "live")
        self.assertTrue(result["preflight_live"])
        self.assertTrue(all(item["mode"] == "live" for item in result["preflight_results"]))

    def test_upload_route_can_require_ai_success(self):
        upload = self._upload(SAMPLE_PLAYBOOK.name, SAMPLE_PLAYBOOK.read_bytes())

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.analyze_playbook_upload(
                upload,
                ai_provider="openai",
                api_key="",
                model="gpt-test",
                ai_required=True,
            )

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("AI interpretation failed", str(ctx.exception.detail))

    def test_upload_route_blocks_malformed_ai_fallback_when_required(self):
        upload = self._upload(SAMPLE_PLAYBOOK.name, SAMPLE_PLAYBOOK.read_bytes())
        original = self.ui_app.run_playbook_agent

        def fake_run(*args, **kwargs):
            return {
                "ai_mode": "fallback",
                "model": "claude-test",
                "review_items": [
                    {
                        "severity": "warning",
                        "message": "Claude interpretation failed: planned_calls[0].params.name must be a string",
                    }
                ],
                "plan_id": "bad-plan",
                "proposed_write_plan": [],
                "parsed_playbook": {"source": {"file_name": SAMPLE_PLAYBOOK.name}},
            }

        try:
            self.ui_app.run_playbook_agent = fake_run
            with self.assertRaises(HTTPException) as ctx:
                self.ui_app.analyze_playbook_upload(
                    upload,
                    ai_provider="anthropic",
                    api_key="test-key",
                    model="claude-test",
                    ai_required=True,
                )
        finally:
            self.ui_app.run_playbook_agent = original

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("planned_calls[0].params.name", str(ctx.exception.detail))

    def test_upload_route_allows_malformed_ai_fallback_when_not_required(self):
        upload = self._upload(SAMPLE_PLAYBOOK.name, SAMPLE_PLAYBOOK.read_bytes())
        original = self.ui_app.run_playbook_agent

        def fake_run(*args, **kwargs):
            return {
                "ai_mode": "fallback",
                "model": "claude-test",
                "review_items": [
                    {
                        "severity": "warning",
                        "message": "Claude interpretation failed: planned_calls[0].params.name must be a string",
                    }
                ],
                "plan_id": "fallback-plan",
                "proposed_write_plan": [{"tool_name": "five9_create_skill", "params": {"name": "Main Agent"}}],
                "parsed_playbook": {"source": {"file_name": SAMPLE_PLAYBOOK.name}},
            }

        try:
            self.ui_app.run_playbook_agent = fake_run
            result = self.ui_app.analyze_playbook_upload(
                upload,
                ai_provider="anthropic",
                api_key="test-key",
                model="claude-test",
                ai_required=False,
            )
        finally:
            self.ui_app.run_playbook_agent = original

        self.assertEqual(result["ai_mode"], "fallback")
        self.assertEqual(result["plan_id"], "fallback-plan")

    def test_upload_route_rejects_serialized_object_names_in_displayed_ai_plan(self):
        upload = self._upload(SAMPLE_PLAYBOOK.name, SAMPLE_PLAYBOOK.read_bytes())
        original = self.ui_app.run_playbook_agent

        def fake_run(*args, **kwargs):
            return {
                "ai_mode": "claude",
                "model": "claude-test",
                "review_items": [],
                "plan_id": "bad-ai-display-plan",
                "ai_planned_calls": [
                    {
                        "tool_name": "five9_create_skill",
                        "params": {
                            "name": "{'name': 'Rehash', 'description': 'Follow-up and rehash team'}",
                            "description": (
                                "Skill imported from implementation playbook: "
                                "{'name': 'Rehash', 'description': 'Follow-up and rehash team'}"
                            ),
                        },
                    }
                ],
                "proposed_write_plan": [
                    {"tool_name": "five9_create_skill", "params": {"name": "Rehash"}}
                ],
                "parsed_playbook": {"source": {"file_name": SAMPLE_PLAYBOOK.name}},
            }

        try:
            self.ui_app.run_playbook_agent = fake_run
            with self.assertRaises(HTTPException) as ctx:
                self.ui_app.analyze_playbook_upload(upload)
        finally:
            self.ui_app.run_playbook_agent = original

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("planned_calls[0].params.name", str(ctx.exception.detail))

    def test_upload_route_returns_json_error_when_agent_runtime_fails(self):
        upload = self._upload(SAMPLE_PLAYBOOK.name, SAMPLE_PLAYBOOK.read_bytes())
        original = self.ui_app.run_playbook_agent

        def fake_run(*args, **kwargs):
            raise RuntimeError("Five9 live preflight failed")

        try:
            self.ui_app.run_playbook_agent = fake_run
            with self.assertRaises(HTTPException) as ctx:
                self.ui_app.analyze_playbook_upload(upload)
        finally:
            self.ui_app.run_playbook_agent = original

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("Five9 live preflight failed", str(ctx.exception.detail))

    def test_execute_route_rejects_missing_approval(self):
        upload = self._upload(SAMPLE_PLAYBOOK.name, SAMPLE_PLAYBOOK.read_bytes())
        analyzed = self.ui_app.analyze_playbook_upload(upload)
        req = self.ui_app.PlaybookAgentExecuteRequest(
            approved=False,
            mode="dry_run",
            plan_id=analyzed["plan_id"],
            planned_calls=analyzed["proposed_write_plan"],
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.execute_playbook_agent(req)

        self.assertEqual(ctx.exception.status_code, 403)

    def test_execute_route_rejects_mutated_plan(self):
        upload = self._upload(SAMPLE_PLAYBOOK.name, SAMPLE_PLAYBOOK.read_bytes())
        analyzed = self.ui_app.analyze_playbook_upload(upload)
        mutated = list(analyzed["proposed_write_plan"])
        mutated.append({"tool_name": "five9_create_skill", "params": {"name": "Injected"}})
        req = self.ui_app.PlaybookAgentExecuteRequest(
            approved=True,
            mode="dry_run",
            plan_id=analyzed["plan_id"],
            planned_calls=mutated,
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.execute_playbook_agent(req)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_live_execute_requires_credentials(self):
        upload = self._upload(SAMPLE_PLAYBOOK.name, SAMPLE_PLAYBOOK.read_bytes())
        analyzed = self.ui_app.analyze_playbook_upload(upload)
        req = self.ui_app.PlaybookAgentExecuteRequest(
            approved=True,
            mode="live",
            plan_id=analyzed["plan_id"],
            planned_calls=analyzed["proposed_write_plan"],
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.execute_playbook_agent(req)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_dry_run_execute_returns_logs(self):
        upload = self._upload(SAMPLE_PLAYBOOK.name, SAMPLE_PLAYBOOK.read_bytes())
        analyzed = self.ui_app.analyze_playbook_upload(upload)
        req = self.ui_app.PlaybookAgentExecuteRequest(
            approved=True,
            mode="dry_run",
            plan_id=analyzed["plan_id"],
            planned_calls=analyzed["proposed_write_plan"],
        )

        result = self.ui_app.execute_playbook_agent(req)

        self.assertEqual(result["summary"]["mode"], "dry_run")
        self.assertEqual(result["summary"]["total"], len(analyzed["proposed_write_plan"]))
        self.assertTrue(all(item["mode"] == "dry_run" for item in result["results"]))
        self.assertTrue(any(item["tool_name"] == "five9_create_ivr_script" for item in result["results"]))

    def test_home_ui_exposes_upload_first_agent_flow(self):
        ui_html = (ROOT / "UI" / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("Playbook Agent", ui_html)
        self.assertIn("/api/agent/playbook/upload-analyze", ui_html)
        self.assertIn("/api/agent/playbook/execute", ui_html)
        self.assertIn('credentialsEndpoint: "/api/credentials/five9"', ui_html)
        self.assertIn("AI Provider", ui_html)
        self.assertIn("OpenAI / ChatGPT", ui_html)
        self.assertIn("Google Gemini", ui_html)
        self.assertIn('id="pb-model"', ui_html)
        self.assertIn('id="pb-model-custom"', ui_html)
        self.assertIn("Custom OpenAI model", ui_html)
        self.assertIn("Require AI success", ui_html)
        self.assertIn("Fallback was used", ui_html)
        self.assertIn("AI Proposed Five9 Operations", ui_html)
        self.assertIn("Live Five9 Preflight", ui_html)
        self.assertIn('id="pb-preflight-mode"', ui_html)
        self.assertIn('id="pb-preflight-username"', ui_html)
        self.assertIn('id="pb-preflight-password"', ui_html)
        self.assertIn("IVR Requirements / Deferred Script Work", ui_html)
        self.assertIn("No IVR XML will be generated or uploaded in this agent slice.", ui_html)
        self.assertIn("IVR Script Shell Create Plan", ui_html)
        self.assertIn("Upload -> AI Interpretation -> Preflight Plan -> Comparison -> Proposed Writes -> Approval -> Execution Log", ui_html)
        self.assertIn("async function readApiResponse", ui_html)
        self.assertIn("await readApiResponse(res)", ui_html)

    def _upload(self, name: str, data: bytes):
        class FakeUpload:
            filename = name

            def __init__(self, payload: bytes):
                self._file = tempfile.SpooledTemporaryFile()
                self._file.write(payload)
                self._file.seek(0)
                self.file = self._file

        return FakeUpload(data)


if __name__ == "__main__":
    unittest.main()
