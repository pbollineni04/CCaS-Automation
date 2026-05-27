import sys
import unittest
from pathlib import Path

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


BUILD_PLAN = {
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


class UIIvrBuilderRouteTests(unittest.TestCase):
    def setUp(self):
        from UI import app as ui_app

        self.ui_app = ui_app

    def test_catalog_route_returns_ai_manual(self):
        result = self.ui_app.get_five9_ivr_builder_catalog()

        self.assertEqual(result["build_plan_schema"], "five9_simple_menu_ivr_v1")
        self.assertIn("module_manual", result)
        self.assertIn("menu", result["modules"])

    def test_validate_plan_route_rejects_duplicate_digits(self):
        plan = {
            **BUILD_PLAN,
            "menu": {
                **BUILD_PLAN["menu"],
                "options": [
                    {"digit": "1", "label": "Sales", "transfer_type": "skill", "target": "Sales"},
                    {"digit": "1", "label": "Billing", "transfer_type": "skill", "target": "Billing"},
                ],
            },
        }
        req = self.ui_app.Five9IvrBuilderPlanRequest(build_plan=plan)

        result = self.ui_app.validate_five9_ivr_builder_plan(req)

        self.assertFalse(result["valid"])
        self.assertIn("duplicate menu digit: 1", result["errors"])

    def test_compile_route_returns_xml_summary_and_planned_call(self):
        req = self.ui_app.Five9IvrBuilderPlanRequest(build_plan=BUILD_PLAN)

        result = self.ui_app.compile_five9_ivr_builder_plan(req)

        self.assertIn("<ivrScript>", result["xmlDefinition"])
        self.assertIn("Main Menu", result["flow_summary"])
        self.assertEqual(result["planned_calls"][0]["tool_name"], "five9_modify_ivr_script")

    def test_visualize_plan_route_returns_nodes_edges_and_palette(self):
        req = self.ui_app.Five9IvrBuilderPlanRequest(build_plan=BUILD_PLAN)

        result = self.ui_app.visualize_five9_ivr_builder_plan(req)

        self.assertTrue(result["valid"])
        self.assertEqual(result["nodes"][0]["module_type"], "incomingCall")
        self.assertIn(
            {"id": "edge_menu_transfer_1", "from": "menu", "to": "transfer_1", "label": "1"},
            result["edges"],
        )
        palette = {entry["module_type"]: entry for entry in result["palette"]}
        self.assertFalse(palette["play"]["locked"])
        self.assertFalse(palette["query"]["locked"])
        self.assertEqual(palette["query"]["generation_status"], "compiler_candidate")

    def test_visualize_plan_route_returns_validation_errors(self):
        plan = {
            **BUILD_PLAN,
            "menu": {
                **BUILD_PLAN["menu"],
                "options": [
                    {"digit": "1", "label": "Sales", "transfer_type": "skill", "target": "Sales"},
                    {"digit": "1", "label": "Billing", "transfer_type": "skill", "target": "Billing"},
                ],
            },
        }
        req = self.ui_app.Five9IvrBuilderPlanRequest(build_plan=plan)

        result = self.ui_app.visualize_five9_ivr_builder_plan(req)

        self.assertFalse(result["valid"])
        self.assertEqual(result["nodes"], [])
        self.assertIn("duplicate menu digit: 1", result["errors"])

    def test_palette_route_returns_builtin_registry_only(self):
        req = self.ui_app.Five9IvrBuilderPaletteRequest()

        result = self.ui_app.get_five9_ivr_builder_palette(req)

        self.assertEqual(result["palette_source"], "builtin_registry")
        palette = {entry["module_type"]: entry for entry in result["modules"]}
        self.assertFalse(palette["skillTransfer"]["locked"])
        self.assertFalse(palette["query"]["locked"])
        self.assertTrue(palette["campaignTransfer"]["locked"])

    def test_compile_canvas_route_returns_xml_summary_and_deploy_status(self):
        canvas = {
            "schema": "five9_ivr_canvas_v1",
            "script_name": "Canvas IVR",
            "nodes": [
                {"id": "incoming", "module_type": "incomingCall", "label": "Incoming"},
                {"id": "play", "module_type": "play", "label": "Greeting", "config": {"prompt_name": "Main", "text": "Hello"}},
                {"id": "query", "module_type": "query", "label": "Lookup", "config": {"url": "https://example.invalid"}},
                {"id": "hangup", "module_type": "hangup", "label": "Hangup"},
            ],
            "edges": [
                {"id": "e1", "source": "incoming", "target": "play", "label": ""},
                {"id": "e2", "source": "play", "target": "query", "label": ""},
                {"id": "e3", "source": "query", "target": "hangup", "label": "success"},
            ],
        }
        req = self.ui_app.Five9IvrBuilderCanvasRequest(canvas=canvas)

        result = self.ui_app.compile_five9_ivr_builder_canvas(req)

        self.assertIn("<query>", result["xmlDefinition"])
        self.assertFalse(result["deployable"])
        self.assertEqual(result["planned_calls"][0]["tool_name"], "five9_modify_ivr_script")

    def test_certification_route_requires_live_approval_and_credentials(self):
        req = self.ui_app.Five9IvrBuilderCertificationRequest(
            mode="live",
            approved=False,
            module_types=["query"],
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.certify_five9_ivr_builder_modules(req)

        self.assertEqual(ctx.exception.status_code, 403)

        req = self.ui_app.Five9IvrBuilderCertificationRequest(
            mode="live",
            approved=True,
            module_types=["query"],
        )
        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.certify_five9_ivr_builder_modules(req)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_runtime_export_analysis_routes_are_disabled(self):
        with self.assertRaises(HTTPException) as file_ctx:
            self.ui_app.analyze_five9_ivr_builder_file(
                self.ui_app.Five9IvrBuilderAnalyzeRequest(
                    file_path=r"C:\Five9 IVR\GenericTest.five9ivr",
                )
            )
        with self.assertRaises(HTTPException) as palette_ctx:
            self.ui_app.analyze_five9_ivr_builder_palette(
                self.ui_app.Five9IvrBuilderAnalyzeRequest(
                    xml_text="<ivrScript/>",
                    script_name="Inline XML",
                )
            )
        with self.assertRaises(HTTPException) as manual_ctx:
            self.ui_app.build_five9_ivr_builder_module_manual(
                self.ui_app.Five9IvrBuilderPaletteRequest(folder_path=r"C:\Five9 IVR")
            )

        self.assertEqual(file_ctx.exception.status_code, 410)
        self.assertEqual(palette_ctx.exception.status_code, 410)
        self.assertEqual(manual_ctx.exception.status_code, 410)

    def test_deploy_route_dry_run_reads_creates_missing_script_then_modifies(self):
        compiled = self.ui_app.compile_five9_ivr_builder_plan(
            self.ui_app.Five9IvrBuilderPlanRequest(build_plan=BUILD_PLAN)
        )
        req = self.ui_app.Five9IvrBuilderDeployRequest(
            mode="dry_run",
            approved=False,
            script_name="Acme Main IVR",
            xml_definition=compiled["xmlDefinition"],
        )

        result = self.ui_app.deploy_five9_ivr_builder_script(req)

        self.assertEqual(result["summary"]["mode"], "dry_run")
        self.assertEqual([item["tool_name"] for item in result["results"]], [
            "five9_get_ivr_scripts",
            "five9_create_ivr_script",
            "five9_modify_ivr_script",
        ])
        self.assertEqual(result["results"][1]["result"], "planned")
        self.assertEqual(result["results"][2]["result"], "planned")

    def test_deploy_route_live_requires_approval(self):
        req = self.ui_app.Five9IvrBuilderDeployRequest(
            mode="live",
            username="user",
            password="pass",
            script_name="Acme Main IVR",
            xml_definition="<ivrScript/>",
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.deploy_five9_ivr_builder_script(req)

        self.assertEqual(ctx.exception.status_code, 403)

    def test_deploy_route_live_requires_credentials(self):
        req = self.ui_app.Five9IvrBuilderDeployRequest(
            mode="live",
            approved=True,
            script_name="Acme Main IVR",
            xml_definition="<ivrScript/>",
        )

        with self.assertRaises(HTTPException) as ctx:
            self.ui_app.deploy_five9_ivr_builder_script(req)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_home_ui_exposes_ivr_script_builder(self):
        ui_html = (ROOT / "UI" / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("Script Builder", ui_html)
        self.assertIn("Visual Flow Canvas", ui_html)
        self.assertIn("Module Palette", ui_html)
        self.assertIn("Menu Option Controls", ui_html)
        self.assertIn("Requirements -&gt; Build Plan -&gt; Compiler Registry -&gt; Generated XML -&gt; Approval -&gt; Five9 Update", ui_html)
        self.assertIn("five9.ivr_builder", ui_html)
        self.assertIn("/api/run/five9/ivr-builder/visualize-plan", ui_html)
        self.assertIn("/api/run/five9/ivr-builder/compile", ui_html)
        self.assertIn("draggable=\"true\"", ui_html)
        self.assertIn("vccStartPaletteDrag", ui_html)
        self.assertIn("vccStartNodeDrag", ui_html)
        self.assertIn("vccDropModule", ui_html)
        self.assertIn("New Blank Script", ui_html)
        self.assertIn("vccStartBlankScript", ui_html)
        self.assertIn("vccImportIvrFile", ui_html)
        self.assertIn("vccShowImportedIvrXml", ui_html)
        self.assertIn("vccToggleConnectMode", ui_html)
        self.assertIn("vccHandleConnectClick", ui_html)
        self.assertIn("vccBuildCanvasFromUi", ui_html)
        self.assertIn("/api/run/five9/ivr-builder/compile-canvas", ui_html)
        self.assertIn("/api/run/five9/ivr-builder/certify", ui_html)
        self.assertIn("ZZ_TEST_Codex_IVR_ModuleLab", ui_html)
        self.assertNotIn("/api/run/five9/ivr-builder/analyze-palette", ui_html)
        self.assertNotIn("/api/run/five9/ivr-builder/module-manual", ui_html)
        self.assertNotIn("C:\\Five9 IVR", ui_html)
        self.assertNotIn("IVR export folder", ui_html)


if __name__ == "__main__":
    unittest.main()
