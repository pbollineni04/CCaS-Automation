"""Five9 tool package.

New code should import from the pack folders. The aliases below preserve older
root-level imports such as ``src.tools.Five9.preflight`` and
``src.tools.Five9.five9_create_skill`` while keeping the filesystem organized.
"""

from importlib import import_module
import sys


_LEGACY_MODULE_ALIASES = {
    "write_common": ".common.write_common",
    "soap_client": ".common.soap_client",
    "preflight": ".preflight_pack.dispatcher",
    "core_writes": ".core_config.dispatcher",
    "modify": ".modify_config.dispatcher",
    "rollback": ".rollback_pack.dispatcher",
    "ivr_scripts": ".ivr.scripts.dispatcher",
    "ivr_builder": ".ivr.builder.facade",
    "ivr_block_registry": ".ivr.builder.block_registry",
    "five9_add_dispositions_to_campaign": ".core_config.five9_add_dispositions_to_campaign",
    "five9_add_dnis_to_campaign": ".core_config.five9_add_dnis_to_campaign",
    "five9_add_prompt_tts": ".core_config.five9_add_prompt_tts",
    "five9_add_skills_to_campaign": ".core_config.five9_add_skills_to_campaign",
    "five9_create_disposition": ".core_config.five9_create_disposition",
    "five9_create_inbound_campaign": ".core_config.five9_create_inbound_campaign",
    "five9_create_skill": ".core_config.five9_create_skill",
    "five9_set_default_ivr_schedule": ".core_config.five9_set_default_ivr_schedule",
    "five9_modify_disposition": ".modify_config.five9_modify_disposition",
    "five9_modify_inbound_campaign": ".modify_config.five9_modify_inbound_campaign",
    "five9_modify_prompt_tts": ".modify_config.five9_modify_prompt_tts",
    "five9_modify_skill": ".modify_config.five9_modify_skill",
    "five9_delete_campaign": ".rollback_pack.five9_delete_campaign",
    "five9_delete_disposition": ".rollback_pack.five9_delete_disposition",
    "five9_delete_prompt": ".rollback_pack.five9_delete_prompt",
    "five9_delete_skill": ".rollback_pack.five9_delete_skill",
    "five9_remove_dispositions_from_campaign": ".rollback_pack.five9_remove_dispositions_from_campaign",
    "five9_remove_dnis_from_campaign": ".rollback_pack.five9_remove_dnis_from_campaign",
    "five9_remove_skills_from_campaign": ".rollback_pack.five9_remove_skills_from_campaign",
    "five9_create_ivr_script": ".ivr.scripts.five9_create_ivr_script",
    "five9_delete_ivr_script": ".ivr.scripts.five9_delete_ivr_script",
    "five9_get_ivr_scripts": ".ivr.scripts.five9_get_ivr_scripts",
    "five9_modify_ivr_script": ".ivr.scripts.five9_modify_ivr_script",
}


for _alias, _target in _LEGACY_MODULE_ALIASES.items():
    _module = import_module(_target, __name__)
    sys.modules[f"{__name__}.{_alias}"] = _module
    globals()[_alias] = _module


__all__ = sorted(_LEGACY_MODULE_ALIASES)
