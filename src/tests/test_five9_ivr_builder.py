import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ivrScript>
  <domainId>140066</domainId>
  <properties/>
  <modules>
    <incomingCall>
      <singleDescendant>PLAY1</singleDescendant>
      <moduleName>START_Test</moduleName>
      <moduleId>START1</moduleId>
      <data/>
    </incomingCall>
    <play>
      <ascendants>START1</ascendants>
      <singleDescendant>MENU1</singleDescendant>
      <moduleName>Greeting</moduleName>
      <moduleId>PLAY1</moduleId>
      <data>
        <prompt>
          <name>Main Greeting</name>
        </prompt>
      </data>
    </play>
    <menu>
      <ascendants>PLAY1</ascendants>
      <moduleName>Main Menu</moduleName>
      <moduleId>MENU1</moduleId>
      <data>
        <branches>
          <entry><key>One</key><value><name>One</name><desc>SKILL1</desc></value></entry>
          <entry><key>Two</key><value><name>Two</name><desc>CAMPAIGN1</desc></value></entry>
          <entry><key>No Match</key><value><name>No Match</name><desc>HANGUP1</desc></value></entry>
        </branches>
      </data>
    </menu>
    <skillTransfer>
      <ascendants>MENU1</ascendants>
      <singleDescendant>HANGUP1</singleDescendant>
      <moduleName>Sales Transfer</moduleName>
      <moduleId>SKILL1</moduleId>
      <data>
        <listOfSkillsEx>
          <extrnalObj><id>1</id><name>Sales</name></extrnalObj>
        </listOfSkillsEx>
      </data>
    </skillTransfer>
    <campaignTransfer>
      <ascendants>MENU1</ascendants>
      <singleDescendant>HANGUP1</singleDescendant>
      <moduleName>Billing Campaign</moduleName>
      <moduleId>CAMPAIGN1</moduleId>
      <data>
        <campaign><name>Billing Inbound</name></campaign>
      </data>
    </campaignTransfer>
    <query>
      <moduleName>Lookup</moduleName>
      <moduleId>QUERY1</moduleId>
      <data><url>https://example.com/lookup</url><method>POST</method></data>
    </query>
    <hangup>
      <ascendants>SKILL1</ascendants>
      <ascendants>CAMPAIGN1</ascendants>
      <moduleName>Done</moduleName>
      <moduleId>HANGUP1</moduleId>
      <data/>
    </hangup>
  </modules>
  <modulesOnHangup/>
  <userVariables>
    <entry><key>callerType</key><value><name>callerType</name><description>Caller category</description></value></entry>
  </userVariables>
  <multiLanguagesPrompts>
    <entry><key>PROMPT1</key><value><name>Main Greeting</name><description>Greeting prompt</description></value></entry>
  </multiLanguagesPrompts>
  <defaultLanguage>en-US</defaultLanguage>
  <version>1300001</version>
</ivrScript>
"""

PALETTE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ivrScript>
  <domainId>140066</domainId>
  <properties/>
  <modules>
    <incomingCall>
      <moduleName>IncomingCall34</moduleName>
      <moduleId>START1</moduleId>
      <data/>
    </incomingCall>
    <menu>
      <moduleName>Menu14</moduleName>
      <moduleId>MENU1</moduleId>
      <data>
        <dispo/>
        <vivrPrompts/>
        <branches/>
        <useSpeechRecognition>false</useSpeechRecognition>
        <useDTMF>true</useDTMF>
      </data>
    </menu>
    <skillTransfer>
      <moduleName>SkillTransfer16</moduleName>
      <moduleId>SKILL1</moduleId>
      <data>
        <dispo/>
        <maxQueueTime>600</maxQueueTime>
        <queueIfOnCall>true</queueIfOnCall>
        <listOfSkillsEx/>
      </data>
    </skillTransfer>
    <query>
      <moduleName>Query22</moduleName>
      <moduleId>QUERY1</moduleId>
      <data>
        <prompt/>
        <method>GET</method>
        <fetchTimeout>5</fetchTimeout>
        <parameters/>
        <returnValues/>
        <headers/>
      </data>
    </query>
  </modules>
  <modulesOnHangup/>
  <userVariables/>
  <multiLanguagesPrompts/>
  <version>1300001</version>
</ivrScript>
"""


VALID_PLAN = {
    "script_name": "Acme Main IVR",
    "description": "Main inbound IVR",
    "greeting": {
        "prompt_name": "Main Greeting",
        "text": "Thank you for calling Acme Health Services.",
    },
    "menu": {
        "name": "Main Menu",
        "options": [
            {"digit": "1", "label": "Sales", "transfer_type": "skill", "target": "Sales"},
            {"digit": "2", "label": "Billing", "transfer_type": "skill", "target": "Billing"},
            {"digit": "3", "label": "Support", "transfer_type": "skill", "target": "Support"},
        ],
        "no_match": "hangup",
        "no_input": "hangup",
    },
}


OBSERVED_MODULE_TYPES = [
    "incomingCall",
    "startOnHangup",
    "hangup",
    "play",
    "menu",
    "getDigits",
    "input",
    "language",
    "recording",
    "setVariable",
    "ifElse",
    "case",
    "iterator",
    "skillTransfer",
    "voiceMailTransfer",
    "thirdPartyTransfer",
    "agentTransfer",
    "extensionTransfer",
    "ivaTransfer",
    "query",
    "foreignScript",
    "lookupCRMRecord",
    "crmUpdate",
    "systemInfo",
    "systemUpdate",
    "setDNC",
    "answerMachine",
    "conference",
]


CANVAS_MODEL = {
    "schema": "five9_ivr_canvas_v1",
    "script_name": "Canvas IVR",
    "description": "Canvas compiler test",
    "nodes": [
        {"id": "incoming", "module_type": "incomingCall", "label": "Incoming Call", "position": {"x": 40, "y": 120}},
        {
            "id": "play",
            "module_type": "play",
            "label": "Greeting",
            "position": {"x": 220, "y": 120},
            "config": {"prompt_name": "Main Greeting", "text": "Thanks for calling."},
        },
        {
            "id": "digits",
            "module_type": "getDigits",
            "label": "Collect Account",
            "position": {"x": 400, "y": 120},
            "config": {"targetVariableName": "acct", "numberOfDigits": 5},
        },
        {
            "id": "flag",
            "module_type": "setVariable",
            "label": "Set Caller Type",
            "position": {"x": 580, "y": 120},
            "config": {"variableName": "callerType", "value": "member"},
        },
        {
            "id": "branch",
            "module_type": "ifElse",
            "label": "Member Branch",
            "position": {"x": 760, "y": 120},
            "config": {"condition": "callerType == member"},
        },
        {
            "id": "sales",
            "module_type": "skillTransfer",
            "label": "Sales Transfer",
            "position": {"x": 950, "y": 70},
            "config": {"target": "Sales"},
        },
        {"id": "hangup", "module_type": "hangup", "label": "Hangup", "position": {"x": 1160, "y": 120}},
    ],
    "edges": [
        {"id": "e1", "source": "incoming", "target": "play", "label": ""},
        {"id": "e2", "source": "play", "target": "digits", "label": ""},
        {"id": "e3", "source": "digits", "target": "flag", "label": ""},
        {"id": "e4", "source": "flag", "target": "branch", "label": ""},
        {"id": "e5", "source": "branch", "target": "sales", "label": "IF"},
        {"id": "e6", "source": "branch", "target": "hangup", "label": "ELSE"},
        {"id": "e7", "source": "sales", "target": "hangup", "label": "success"},
    ],
}


class Five9IvrBuilderTests(unittest.TestCase):
    def setUp(self):
        from src.tools.Five9 import ivr_builder

        self.ivr_builder = ivr_builder

    def test_parser_extracts_modules_edges_branches_variables_prompts_and_targets(self):
        summary = self.ivr_builder.parse_ivr_xml(SAMPLE_XML, script_name="Sample")

        self.assertEqual(summary["script_name"], "Sample")
        self.assertEqual(summary["module_counts"]["menu"], 1)
        self.assertEqual(summary["module_counts"]["skillTransfer"], 1)
        menu_module = next(module for module in summary["modules"] if module["module_type"] == "menu")
        self.assertEqual(menu_module["data_fields"], ["branches"])
        self.assertEqual(menu_module["connection_status"], "connected")
        self.assertIn(
            {"from": "MENU1", "to": "SKILL1", "type": "branch", "label": "One"},
            summary["edges"],
        )
        self.assertIn(
            {"module_id": "SKILL1", "module_type": "skillTransfer", "targets": ["Sales"]},
            summary["transfer_targets"],
        )
        self.assertIn(
            {"module_id": "QUERY1", "module_name": "Lookup", "url": "https://example.com/lookup", "method": "POST"},
            summary["queries"],
        )
        self.assertEqual(summary["variables"][0]["name"], "callerType")
        self.assertEqual(summary["prompts"][0]["name"], "Main Greeting")

    def test_analyze_file_and_folder_parse_five9ivr_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            first = folder / "Sample.five9ivr"
            second = folder / "Other.five9ivr"
            first.write_text(SAMPLE_XML, encoding="utf-8")
            second.write_text(SAMPLE_XML.replace("START_Test", "START_Other"), encoding="utf-8")

            one = self.ivr_builder.analyze_ivr_file(str(first))
            many = self.ivr_builder.analyze_ivr_export_folder(str(folder))

        self.assertEqual(one["script_name"], "Sample")
        self.assertEqual(len(many), 2)
        self.assertEqual([item["script_name"] for item in many], ["Other", "Sample"])

    def test_palette_analyzer_extracts_non_deployable_module_manual(self):
        palette = self.ivr_builder.analyze_module_palette(PALETTE_XML, script_name="All Modules")

        self.assertEqual(palette["script_name"], "All Modules")
        self.assertFalse(palette["deployable"])
        self.assertIn("No executable main-flow edges were found", palette["warnings"])
        self.assertEqual(palette["module_count"], 4)
        self.assertEqual(palette["catalog"]["menu"]["data_fields"], ["branches", "dispo", "useDTMF", "useSpeechRecognition", "vivrPrompts"])
        self.assertEqual(palette["catalog"]["query"]["generation_status"], "compiler_candidate")
        self.assertIn("maxQueueTime", palette["catalog"]["skillTransfer"]["data_fields"])
        self.assertIn("incomingCall", palette["unconnected_modules"])

    def test_analyze_palette_file_reads_five9ivr_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "All Modules.five9ivr"
            path.write_text(PALETTE_XML, encoding="utf-8")

            palette = self.ivr_builder.analyze_module_palette_file(str(path))

        self.assertEqual(palette["script_name"], "All Modules")
        self.assertIn("menu", palette["catalog"])

    def test_catalog_is_ai_readable_and_marks_v1_supported_modules(self):
        catalog = self.ivr_builder.get_ivr_builder_catalog()

        self.assertEqual(catalog["build_plan_schema"], "five9_simple_menu_ivr_v1")
        self.assertEqual(catalog["modules"]["menu"]["generation_status"], "supported_v1")
        self.assertEqual(catalog["modules"]["skillTransfer"]["generation_status"], "supported_v1")
        self.assertEqual(catalog["modules"]["campaignTransfer"]["generation_status"], "unsupported_no_corpus_evidence")
        self.assertEqual(catalog["modules"]["query"]["generation_status"], "compiler_candidate")
        self.assertEqual(catalog["modules"]["query"]["certification"]["status"], "pending")
        for module_type in OBSERVED_MODULE_TYPES:
            self.assertIn(module_type, catalog["modules"])
            self.assertIn(catalog["modules"][module_type]["generation_status"], {"supported_v1", "compiler_candidate"})
        self.assertIn("digit", catalog["modules"]["menu"]["required_fields"])
        self.assertIn("real Five9 XML exports", catalog["module_manual"])
        self.assertNotIn("C:\\Five9 IVR", str(catalog))

    def test_visualize_valid_build_plan_returns_nodes_edges_and_palette(self):
        visual = self.ivr_builder.visualize_build_plan(VALID_PLAN)

        self.assertTrue(visual["valid"])
        self.assertEqual(visual["errors"], [])
        self.assertEqual([node["id"] for node in visual["nodes"]], [
            "incoming",
            "greeting",
            "menu",
            "transfer_1",
            "transfer_2",
            "transfer_3",
            "hangup",
        ])
        self.assertIn(
            {"id": "edge_menu_transfer_1", "from": "menu", "to": "transfer_1", "label": "1"},
            visual["edges"],
        )
        self.assertIn(
            {"id": "edge_transfer_3_hangup", "from": "transfer_3", "to": "hangup", "label": "success"},
            visual["edges"],
        )
        self.assertEqual(visual["nodes"][4]["module_type"], "skillTransfer")
        self.assertEqual(visual["nodes"][4]["target"], "Billing")

        palette = {entry["module_type"]: entry for entry in visual["palette"]}
        self.assertFalse(palette["menu"]["locked"])
        self.assertFalse(palette["query"]["locked"])
        self.assertEqual(palette["query"]["status_label"], "Compiler candidate; live certification pending")

    def test_visualize_uses_build_plan_layout_positions(self):
        plan = {
            **VALID_PLAN,
            "layout": {
                "incoming": {"x": 70, "y": 90},
                "greeting": {"x": 260, "y": 130},
                "menu": {"x": 480, "y": 170},
                "transfer_2": {"x": 790, "y": 245},
                "hangup": {"x": 1060, "y": 200},
            },
        }

        visual = self.ivr_builder.visualize_build_plan(plan)
        by_id = {node["id"]: node for node in visual["nodes"]}

        self.assertEqual(by_id["incoming"]["x"], 70)
        self.assertEqual(by_id["incoming"]["y"], 90)
        self.assertEqual(by_id["transfer_2"]["x"], 790)
        self.assertEqual(by_id["transfer_2"]["y"], 245)

    def test_visualize_invalid_build_plan_returns_validation_errors(self):
        plan = {
            **VALID_PLAN,
            "menu": {
                **VALID_PLAN["menu"],
                "options": [
                    {"digit": "1", "label": "Sales", "transfer_type": "skill", "target": "Sales"},
                    {"digit": "1", "label": "Billing", "transfer_type": "skill", "target": "Billing"},
                ],
            },
        }

        visual = self.ivr_builder.visualize_build_plan(plan)

        self.assertFalse(visual["valid"])
        self.assertEqual(visual["nodes"], [])
        self.assertIn("duplicate menu digit: 1", visual["errors"])

    def test_visualize_rejects_campaign_transfer_until_corpus_shape_is_proven(self):
        plan = {
            **VALID_PLAN,
            "menu": {
                **VALID_PLAN["menu"],
                "options": [
                    {"digit": "1", "label": "Sales", "transfer_type": "campaign", "target": "Sales Inbound"},
                ],
            },
        }

        visual = self.ivr_builder.visualize_build_plan(plan)

        self.assertFalse(visual["valid"])
        self.assertIn("campaign transfer is not compiler-supported until a real export proves the XML shape", visual["errors"])

    def test_valid_build_plan_returns_preflight_requirements(self):
        result = self.ivr_builder.validate_build_plan(VALID_PLAN)

        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["required_preflight_objects"]["skills"], ["Sales", "Billing", "Support"])
        self.assertEqual(result["required_preflight_objects"]["prompts"], ["Main Greeting"])

    def test_invalid_build_plans_reject_common_ai_mistakes(self):
        cases = [
            ({**VALID_PLAN, "script_name": " "}, "script_name is required"),
            ({**VALID_PLAN, "menu": {**VALID_PLAN["menu"], "options": []}}, "menu.options must include at least one option"),
            (
                {
                    **VALID_PLAN,
                    "menu": {
                        **VALID_PLAN["menu"],
                        "options": [
                            {"digit": "1", "label": "Sales", "transfer_type": "skill", "target": "Sales"},
                            {"digit": "1", "label": "Billing", "transfer_type": "skill", "target": "Billing"},
                        ],
                    },
                },
                "duplicate menu digit: 1",
            ),
            (
                {
                    **VALID_PLAN,
                    "menu": {
                        **VALID_PLAN["menu"],
                        "options": [{"digit": "1", "label": "API", "transfer_type": "query", "target": "Lookup"}],
                    },
                },
                "unsupported transfer_type: query",
            ),
            (
                {
                    **VALID_PLAN,
                    "menu": {
                        **VALID_PLAN["menu"],
                        "options": [{"digit": "1", "label": "Sales", "transfer_type": "campaign", "target": "Sales Inbound"}],
                    },
                },
                "campaign transfer is not compiler-supported until a real export proves the XML shape",
            ),
            ({**VALID_PLAN, "modules": [{"type": "query"}]}, "raw module requests are not supported in v1"),
        ]

        for plan, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                result = self.ivr_builder.validate_build_plan(plan)
                self.assertFalse(result["valid"])
                self.assertIn(expected_error, result["errors"])

    def test_compiler_generates_valid_five9_xml_and_planned_modify_call(self):
        result = self.ivr_builder.compile_simple_menu_ivr(VALID_PLAN)
        root = ET.fromstring(result["xmlDefinition"])
        modules = root.find("modules")
        module_ids = {module.findtext("moduleId") for module in modules}
        target_ids = [
            node.text
            for node in modules.findall(".//singleDescendant")
            if node.text
        ] + [
            node.text
            for node in modules.findall(".//branches/entry/value/desc")
            if node.text
        ]

        self.assertEqual(root.tag, "ivrScript")
        self.assertIsNotNone(root.find("modulesOnHangup"))
        hangup_modules = root.find("modulesOnHangup")
        self.assertEqual(hangup_modules[0].tag, "startOnHangup")
        self.assertEqual(hangup_modules[1].tag, "hangup")
        self.assertEqual(hangup_modules[0].findtext("singleDescendant"), hangup_modules[1].findtext("moduleId"))
        self.assertIsNotNone(root.find("multiLanguagesPrompts"))
        self.assertIsNotNone(root.find("./modules/play/data/prompt/ttsPrompt/xml"))
        self.assertIsNotNone(root.find("./modules/play/data/textChannelData/textPrompts"))
        self.assertIsNotNone(root.find("./modules/menu/data/items/dtmf"))
        self.assertIsNotNone(root.find("./modules/menu/data/recoEvents"))
        self.assertIsNotNone(root.find("./modules/skillTransfer/data/announcements"))
        self.assertIsNotNone(root.find("./modules/skillTransfer/data/transferAlgorithm"))
        self.assertIsNotNone(root.find("./modules/hangup/data/errCode/integerValue/value"))
        self.assertIn("Main Menu", result["flow_summary"])
        self.assertTrue(all(target_id in module_ids for target_id in target_ids))
        self.assertEqual(result["planned_calls"][0]["tool_name"], "five9_modify_ivr_script")
        self.assertEqual(result["planned_calls"][0]["params"]["name"], "Acme Main IVR")
        self.assertEqual(result["planned_calls"][0]["params"]["xml_definition"], result["xmlDefinition"])

    def test_compiler_writes_build_plan_layout_to_module_coordinates(self):
        plan = {
            **VALID_PLAN,
            "layout": {
                "greeting": {"x": 250, "y": 111},
                "menu": {"x": 500, "y": 222},
                "transfer_2": {"x": 760, "y": 333},
                "hangup": {"x": 1000, "y": 444},
            },
        }

        root = ET.fromstring(self.ivr_builder.compile_simple_menu_ivr(plan)["xmlDefinition"])
        modules = root.find("modules")
        by_name = {module.findtext("moduleName"): module for module in modules}
        billing_transfer = next(
            module
            for module in modules
            if module.tag == "skillTransfer" and module.findtext("./data/listOfSkillsEx/extrnalObj/name") == "Billing"
        )

        self.assertEqual(by_name["Greeting"].findtext("locationX"), "250")
        self.assertEqual(by_name["Greeting"].findtext("locationY"), "111")
        self.assertEqual(by_name["Main Menu"].findtext("locationX"), "500")
        self.assertEqual(by_name["Main Menu"].findtext("locationY"), "222")
        self.assertEqual(billing_transfer.findtext("locationX"), "760")
        self.assertEqual(billing_transfer.findtext("locationY"), "333")
        self.assertEqual(by_name["END_Acme_Main_IVR"].findtext("locationY"), "444")

    def test_compiler_rejects_campaign_transfer(self):
        plan = {
            **VALID_PLAN,
            "menu": {
                **VALID_PLAN["menu"],
                "options": [
                    {"digit": "1", "label": "Sales", "transfer_type": "campaign", "target": "Sales Inbound"},
                ],
            },
        }

        with self.assertRaisesRegex(ValueError, "campaign transfer is not compiler-supported"):
            self.ivr_builder.compile_simple_menu_ivr(plan)

    def test_static_palette_does_not_read_local_export_folder_by_default(self):
        palette = self.ivr_builder.get_ivr_builder_palette()

        self.assertEqual(palette["palette_source"], "builtin_registry")
        self.assertEqual(palette["warnings"], [])
        by_type = {entry["module_type"]: entry for entry in palette["modules"]}
        self.assertTrue(by_type["menu"]["supported"])
        self.assertTrue(by_type["query"]["supported"])
        self.assertEqual(by_type["query"]["generation_status"], "compiler_candidate")
        self.assertTrue(by_type["campaignTransfer"]["locked"])
        self.assertEqual(by_type["campaignTransfer"]["generation_status"], "unsupported_no_corpus_evidence")

    def test_compile_rejects_invalid_plan(self):
        with self.assertRaisesRegex(ValueError, "script_name is required"):
            self.ivr_builder.compile_simple_menu_ivr({**VALID_PLAN, "script_name": ""})

    def test_canvas_compiler_emits_corpus_backed_candidate_modules(self):
        result = self.ivr_builder.compile_canvas_ivr(CANVAS_MODEL)
        root = ET.fromstring(result["xmlDefinition"])
        modules = root.find("modules")
        module_ids = {module.findtext("moduleId") for module in modules}
        target_ids = [
            node.text
            for node in modules.findall(".//singleDescendant")
            if node.text
        ] + [
            node.text
            for node in modules.findall(".//branches/entry/value/desc")
            if node.text
        ]

        self.assertTrue(result["validation"]["valid"])
        self.assertFalse(result["deployable"])
        self.assertIn("uncertified module factories", result["validation"]["warnings"][0])
        for module_type in ("incomingCall", "play", "getDigits", "setVariable", "ifElse", "skillTransfer", "hangup"):
            self.assertIsNotNone(root.find(f"./modules/{module_type}"))
        self.assertTrue(all(target_id in module_ids for target_id in target_ids))
        self.assertIsNotNone(root.find("./modulesOnHangup/startOnHangup"))
        self.assertEqual(result["planned_calls"][0]["tool_name"], "five9_modify_ivr_script")

    def test_query_candidate_uses_required_corpus_backed_defaults(self):
        result = self.ivr_builder.compile_canvas_ivr(
            self.ivr_builder._certification_canvas("ZZ_TEST_Codex_IVR_ModuleLab", "query")
        )
        root = ET.fromstring(result["xmlDefinition"])
        query_data = root.find("./modules/query/data")

        self.assertIsNotNone(query_data.find("prompt/interruptible"))
        self.assertEqual(query_data.findtext("prompt/interruptible"), "false")
        self.assertIsNotNone(query_data.find("vivrPrompts/ttsEnumed"))
        self.assertIsNotNone(query_data.find("vivrHeader/exitModuleOnException"))
        self.assertEqual(query_data.findtext("textChannelData/isUsedVivrPrompts"), "true")
        self.assertEqual(query_data.findtext("textChannelData/isTextOnly"), "true")
        self.assertEqual(query_data.findtext("storeNumberOfArrayElementsInVariable"), "false")
        self.assertEqual(query_data.findtext("requestInfo/template/base64"), "H4sIAAAAAAAAAAMAAAAAAAAAAAA=")
        self.assertIsNotNone(query_data.find("responseInfos/regexp/regexpFlags"))
        self.assertEqual(query_data.findtext("saveStatusCode"), "false")
        self.assertEqual(query_data.findtext("saveReasonPhrase"), "false")
        self.assertNotIn(".invalid", query_data.findtext("url"))

    def test_canvas_compiler_has_factories_for_all_observed_module_candidates(self):
        nodes = [
            {
                "id": f"node_{index}",
                "module_type": module_type,
                "label": module_type,
                "position": {"x": 80 + index * 30, "y": 100 + index * 8},
                "config": {"target": "Sales", "url": "https://example.invalid/api"},
            }
            for index, module_type in enumerate(module_type for module_type in OBSERVED_MODULE_TYPES if module_type != "startOnHangup")
        ]
        edges = [
            {"id": f"edge_{index}", "source": nodes[index]["id"], "target": nodes[index + 1]["id"], "label": "success"}
            for index in range(len(nodes) - 1)
        ]
        canvas = {
            "schema": "five9_ivr_canvas_v1",
            "script_name": "All Observed Candidate Modules",
            "nodes": nodes,
            "edges": edges,
        }

        result = self.ivr_builder.compile_canvas_ivr(canvas)
        root = ET.fromstring(result["xmlDefinition"])

        self.assertTrue(result["validation"]["valid"])
        for module_type in {node["module_type"] for node in nodes}:
            self.assertIsNotNone(root.find(f"./modules/{module_type}"), module_type)

    def test_canvas_compiler_rejects_campaign_transfer_until_real_export_exists(self):
        canvas = {
            **CANVAS_MODEL,
            "nodes": [
                {"id": "incoming", "module_type": "incomingCall", "label": "Incoming"},
                {"id": "campaign", "module_type": "campaignTransfer", "label": "Campaign", "config": {"target": "Sales"}},
                {"id": "hangup", "module_type": "hangup", "label": "Hangup"},
            ],
            "edges": [
                {"id": "e1", "source": "incoming", "target": "campaign", "label": ""},
                {"id": "e2", "source": "campaign", "target": "hangup", "label": "success"},
            ],
        }

        with self.assertRaisesRegex(ValueError, "campaignTransfer is locked"):
            self.ivr_builder.compile_canvas_ivr(canvas)

    def test_certification_flow_is_dry_run_by_default_and_gated_for_live(self):
        dry_run = self.ivr_builder.certify_module_factories(
            module_types=["query"],
            mode="dry_run",
            approved=False,
        )

        self.assertEqual(dry_run["summary"]["mode"], "dry_run")
        self.assertEqual(dry_run["results"][0]["result"], "planned")
        self.assertEqual(dry_run["results"][0]["script_name"], "ZZ_TEST_Codex_IVR_ModuleLab")

        with self.assertRaises(PermissionError):
            self.ivr_builder.certify_module_factories(
                module_types=["query"],
                mode="live",
                approved=False,
                client=object(),
            )
        with self.assertRaises(ValueError):
            self.ivr_builder.certify_module_factories(
                module_types=["query"],
                mode="live",
                approved=True,
                client=None,
            )

    def test_certification_flow_live_uses_modify_and_readback_client_methods(self):
        class FakeClient:
            def __init__(self):
                self.modified = []
                self.readbacks = []
                self.created = []

            def modify_ivr_script(self, name, description=None, xml_definition=None):
                self.modified.append((name, description, xml_definition))
                return {"ok": True}

            def create_ivr_script(self, name):
                self.created.append(name)
                return {"created": name}

            def get_ivr_scripts(self, name_pattern=None):
                self.readbacks.append(name_pattern)
                return [{"name": "ZZ_TEST_Codex_IVR_ModuleLab", "xmlDefinition": "<ivrScript/>"}]

        client = FakeClient()

        result = self.ivr_builder.certify_module_factories(
            module_types=["query"],
            mode="live",
            approved=True,
            client=client,
        )

        self.assertEqual(result["results"][0]["result"], "success")
        self.assertEqual(client.created, [])
        self.assertEqual(client.modified[0][0], "ZZ_TEST_Codex_IVR_ModuleLab")
        self.assertEqual(client.readbacks, ["^ZZ_TEST_Codex_IVR_ModuleLab$", "ZZ_TEST_Codex_IVR_ModuleLab"])


if __name__ == "__main__":
    unittest.main()
