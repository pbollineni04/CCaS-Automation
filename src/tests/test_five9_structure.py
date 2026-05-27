import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class Five9StructureTests(unittest.TestCase):
    def test_pack_dispatchers_have_logical_package_imports(self):
        expected = {
            "src.tools.Five9.preflight_pack.dispatcher": "five9_get_skills",
            "src.tools.Five9.core_config.dispatcher": "execute_core_write_plan",
            "src.tools.Five9.modify_config.dispatcher": "execute_modify_plan",
            "src.tools.Five9.rollback_pack.dispatcher": "execute_rollback_plan",
            "src.tools.Five9.ivr.scripts.dispatcher": "execute_ivr_script_plan",
            "src.tools.Five9.ivr.builder.facade": "compile_simple_menu_ivr",
            "src.tools.Five9.common.soap_client": "Five9ConfigClient",
            "src.tools.Five9.common.write_common": "build_write_result",
        }

        for module_name, symbol in expected.items():
            with self.subTest(module_name=module_name):
                module = importlib.import_module(module_name)
                self.assertTrue(hasattr(module, symbol))

    def test_legacy_import_paths_remain_compatible(self):
        legacy_expected = {
            "src.tools.Five9.preflight": "five9_get_skills",
            "src.tools.Five9.core_writes": "execute_core_write_plan",
            "src.tools.Five9.modify": "execute_modify_plan",
            "src.tools.Five9.rollback": "execute_rollback_plan",
            "src.tools.Five9.ivr_scripts": "execute_ivr_script_plan",
            "src.tools.Five9.ivr_builder": "compile_simple_menu_ivr",
            "src.tools.Five9.soap_client": "Five9ConfigClient",
            "src.tools.Five9.write_common": "build_write_result",
            "src.tools.Five9.five9_create_skill": "five9_create_skill",
            "src.tools.Five9.five9_modify_skill": "five9_modify_skill",
            "src.tools.Five9.five9_delete_skill": "five9_delete_skill",
            "src.tools.Five9.five9_get_ivr_scripts": "five9_get_ivr_scripts",
        }

        for module_name, symbol in legacy_expected.items():
            with self.subTest(module_name=module_name):
                module = importlib.import_module(module_name)
                self.assertTrue(hasattr(module, symbol))


if __name__ == "__main__":
    unittest.main()
