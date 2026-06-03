import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class WorkspaceStructureTests(unittest.TestCase):
    def test_python_workspaces_have_explicit_package_markers(self):
        expected = [
            "src/__init__.py",
            "src/agent/__init__.py",
            "src/tests/__init__.py",
            "src/tools/__init__.py",
            "src/tools/cxone/__init__.py",
            "src/tools/zoom_cc/__init__.py",
            "src/utils/__init__.py",
        ]

        missing = [path for path in expected if not (ROOT / path).exists()]

        self.assertEqual([], missing)

    def test_ui_imports_five9_pack_modules_directly(self):
        app_source = (ROOT / "UI" / "app.py").read_text(encoding="utf-8")

        expected_imports = [
            "from src.tools.Five9.preflight_pack import dispatcher as five9_preflight",
            "from src.tools.Five9.core_config import dispatcher as five9_core_writes",
            "from src.tools.Five9.modify_config import dispatcher as five9_modify",
            "from src.tools.Five9.rollback_pack import dispatcher as five9_rollback",
            "from src.tools.Five9.ivr.scripts import dispatcher as five9_ivr_scripts",
            "from src.tools.Five9.ivr.builder import facade as five9_ivr_builder",
            "from src.tools.Five9.common.soap_client import Five9ConfigClient",
        ]
        legacy_imports = [
            "from src.tools.Five9 import preflight",
            "from src.tools.Five9 import core_writes",
            "from src.tools.Five9 import modify",
            "from src.tools.Five9 import rollback",
            "from src.tools.Five9 import ivr_scripts",
            "from src.tools.Five9 import ivr_builder",
            "from src.tools.Five9.soap_client import Five9ConfigClient",
        ]

        for expected in expected_imports:
            self.assertIn(expected, app_source)
        for legacy in legacy_imports:
            self.assertNotIn(legacy, app_source)

    def test_root_routing_docs_describe_current_live_safety_model(self):
        for filename in ["CLAUDE.md", "AGENTS.md", "README.md"]:
            text = (ROOT / filename).read_text(encoding="utf-8")

            self.assertIn("Dry-run/stub mode is the default", text)
            self.assertIn("Live tool calls require explicit human approval", text)
            self.assertNotIn("Stub tools only until explicitly told to wire live APIs", text)

    def test_workspace_contexts_reference_current_pack_layout(self):
        src_context = (ROOT / "src" / "CONTEXT.md").read_text(encoding="utf-8")
        ui_context = (ROOT / "UI" / "CONTEXT.md").read_text(encoding="utf-8")

        for pack_name in [
            "preflight_pack/",
            "core_config/",
            "modify_config/",
            "rollback_pack/",
            "ivr/scripts/",
            "ivr/builder/",
        ]:
            self.assertIn(pack_name, src_context)

        self.assertIn("pack dispatchers and facades", ui_context)

    def test_ui_splits_main_and_test_tool_surfaces(self):
        app_source = (ROOT / "UI" / "app.py").read_text(encoding="utf-8")
        ui_html = (ROOT / "UI" / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn('@app.get("/test")', app_source)
        self.assertIn("MAIN_TOOL_IDS", ui_html)
        self.assertIn('"five9.playbook_agent"', ui_html)
        self.assertIn('"five9.prompt_bulk_upload"', ui_html)
        self.assertIn("TEST_TOOL_IDS", ui_html)
        self.assertIn('"five9.core_writes"', ui_html)
        self.assertIn('window.location.pathname.replace(/\\/+$/, "") === "/test"', ui_html)


if __name__ == "__main__":
    unittest.main()
