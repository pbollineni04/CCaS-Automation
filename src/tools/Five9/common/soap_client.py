from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from lxml import etree
from requests.auth import HTTPBasicAuth


ENDPOINT = "https://{domain}/wsadmin/v13/AdminWebService"
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
SER_NS = "http://service.admin.ws.five9.com/"
HEADERS = {"Content-Type": "text/xml;charset=UTF-8", "SOAPAction": '""'}


@dataclass(frozen=True)
class Five9Credentials:
    username: str
    password: str
    domain: str = "api.five9.com"


class Five9ConfigClient:
    def __init__(
        self,
        username: str,
        password: str,
        domain: str = "api.five9.com",
        session: Any | None = None,
        timeout: int = 60,
    ):
        self._url = ENDPOINT.format(domain=domain)
        self._timeout = timeout
        self._session = session or requests.Session()
        self._session.auth = HTTPBasicAuth(username, password)
        self._session.headers.update(HEADERS)

    @classmethod
    def from_credentials(
        cls,
        credentials: Five9Credentials,
        session: Any | None = None,
        timeout: int = 60,
    ) -> "Five9ConfigClient":
        return cls(
            username=credentials.username,
            password=credentials.password,
            domain=credentials.domain,
            session=session,
            timeout=timeout,
        )

    def get_skills(self, name_pattern: str | None = None) -> list[dict[str, Any]]:
        inner_xml = _optional_element("skillNamePattern", name_pattern)
        root = self._call("getSkills", inner_xml)
        return _response_items(root, ("return",))

    def get_dispositions(
        self,
        name_pattern: str | None = None,
    ) -> list[dict[str, Any]]:
        inner_xml = _optional_element("dispositionNamePattern", name_pattern)
        root = self._call("getDispositions", inner_xml)
        return _response_items(root, ("return",))

    def get_prompts(self) -> list[dict[str, Any]]:
        root = self._call("getPrompts", "")
        return _response_items(root, ("prompts", "return"))

    def get_campaigns(
        self,
        name_pattern: str | None = None,
        campaign_type: str | None = None,
    ) -> list[dict[str, Any]]:
        inner_xml = (
            _optional_element("campaignNamePattern", name_pattern)
            + _optional_element("campaignType", campaign_type)
        )
        root = self._call("getCampaigns", inner_xml)
        return _response_items(root, ("return",))

    def get_dnis_list(self, select_unassigned: bool = False) -> list[str]:
        inner_xml = _element("selectUnassigned", _bool_text(select_unassigned))
        root = self._call("getDNISList", inner_xml)
        return [str(item) for item in _response_items(root, ("return",))]

    def get_campaign_dnis_list(self, campaign_name: str) -> list[str]:
        root = self._call("getCampaignDNISList", _element("campaignName", campaign_name))
        return [str(item) for item in _response_items(root, ("return",))]

    def get_ivr_scripts(
        self,
        name_pattern: str | None = None,
    ) -> list[dict[str, Any]]:
        root = self._call("getIVRScripts", _optional_element("namePattern", name_pattern))
        return _response_items(root, ("return",))

    def create_skill(
        self,
        name: str,
        description: str | None = None,
        route_voice_mails: bool | None = None,
        message_of_the_day: str | None = None,
    ) -> dict[str, Any]:
        skill = _object_xml(
            "skill",
            {
                "description": description,
                "messageOfTheDay": message_of_the_day,
                "name": name,
                "routeVoiceMails": route_voice_mails,
            },
        )
        root = self._call("createSkill", _object_xml("skillInfo", {"skill": _raw(skill)}))
        return _write_result(root)

    def create_disposition(
        self,
        name: str,
        description: str | None = None,
        agent_must_complete_worksheet: bool | None = None,
        agent_must_confirm: bool | None = None,
        reset_attempts_counter: bool | None = None,
    ) -> dict[str, Any]:
        root = self._call(
            "createDisposition",
            _object_xml(
                "disposition",
                {
                    "agentMustCompleteWorksheet": agent_must_complete_worksheet,
                    "agentMustConfirm": agent_must_confirm,
                    "description": description,
                    "name": name,
                    "resetAttemptsCounter": reset_attempts_counter,
                },
            ),
        )
        return _write_result(root)

    def add_prompt_tts(
        self,
        prompt_name: str,
        text: str,
        description: str | None = None,
        voice: str | None = None,
        language: str | None = None,
    ) -> dict[str, Any]:
        root = self._call(
            "addPromptTTS",
            _object_xml(
                "prompt",
                {
                    "description": description,
                    "name": prompt_name,
                    "type": "TTSGenerated",
                },
            )
            + _object_xml(
                "ttsInfo",
                {
                    "language": language,
                    "text": text,
                    "voice": voice,
                },
            ),
        )
        return _write_result(root)

    def create_inbound_campaign(
        self,
        campaign_name: str,
        description: str | None = None,
        max_num_of_lines: int | None = None,
    ) -> dict[str, Any]:
        root = self._call(
            "createInboundCampaign",
            _object_xml(
                "campaign",
                {
                    "description": description,
                    "maxNumOfLines": max_num_of_lines,
                    "name": campaign_name,
                },
            ),
        )
        return _write_result(root)

    def add_dnis_to_campaign(
        self,
        campaign_name: str,
        dnis: list[str],
    ) -> dict[str, Any]:
        root = self._call(
            "addDNISToCampaign",
            _element("campaignName", campaign_name)
            + _repeated_elements("DNISList", dnis),
        )
        return _write_result(root)

    def add_skills_to_campaign(
        self,
        campaign_name: str,
        skills: list[str],
    ) -> dict[str, Any]:
        root = self._call(
            "addSkillsToCampaign",
            _element("campaignName", campaign_name)
            + _repeated_elements("skills", skills),
        )
        return _write_result(root)

    def add_dispositions_to_campaign(
        self,
        campaign_name: str,
        dispositions: list[str],
        is_skip_preview_disposition: bool | None = None,
    ) -> dict[str, Any]:
        root = self._call(
            "addDispositionsToCampaign",
            _element("campaignName", campaign_name)
            + _repeated_elements("dispositions", dispositions)
            + _optional_element(
                "isSkipPreviewDisposition",
                None if is_skip_preview_disposition is None else _bool_text(is_skip_preview_disposition),
            ),
        )
        return _write_result(root)

    def set_default_ivr_schedule(
        self,
        campaign_name: str,
        script_name: str,
        params: dict[str, Any] | None = None,
        is_visual_mode_enabled: bool | None = None,
    ) -> dict[str, Any]:
        root = self._call(
            "setDefaultIVRSchedule",
            _element("campaignName", campaign_name)
            + _element("scriptName", script_name)
            + _script_params_xml(params or {})
            + _optional_element(
                "isVisualModeEnabled",
                None if is_visual_mode_enabled is None else _bool_text(is_visual_mode_enabled),
            ),
        )
        return _write_result(root)

    def create_ivr_script(self, name: str) -> dict[str, Any]:
        root = self._call("createIVRScript", _element("name", name))
        return _write_result(root)

    def modify_ivr_script(
        self,
        name: str,
        description: str | None = None,
        xml_definition: str | None = None,
    ) -> dict[str, Any]:
        root = self._call(
            "modifyIVRScript",
            _object_xml(
                "scriptDef",
                {
                    "description": description,
                    "name": name,
                    "xmlDefinition": xml_definition,
                },
            ),
        )
        return _write_result(root)

    def delete_ivr_script(self, name: str) -> dict[str, Any]:
        root = self._call("deleteIVRScript", _element("name", name))
        return _write_result(root)

    def modify_skill(
        self,
        skill_name: str,
        description: str | None = None,
        route_voice_mails: bool | None = None,
        message_of_the_day: str | None = None,
    ) -> dict[str, Any]:
        root = self._call(
            "modifySkill",
            _object_xml(
                "skill",
                {
                    "description": description,
                    "messageOfTheDay": message_of_the_day,
                    "name": skill_name,
                    "routeVoiceMails": route_voice_mails,
                },
            ),
        )
        return _write_result(root)

    def modify_disposition(
        self,
        name: str,
        description: str | None = None,
        agent_must_complete_worksheet: bool | None = None,
        agent_must_confirm: bool | None = None,
        reset_attempts_counter: bool | None = None,
    ) -> dict[str, Any]:
        root = self._call(
            "modifyDisposition",
            _object_xml(
                "disposition",
                {
                    "agentMustCompleteWorksheet": agent_must_complete_worksheet,
                    "agentMustConfirm": agent_must_confirm,
                    "description": description,
                    "name": name,
                    "resetAttemptsCounter": reset_attempts_counter,
                },
            ),
        )
        return _write_result(root)

    def modify_prompt_tts(
        self,
        prompt_name: str,
        text: str,
        description: str | None = None,
        voice: str | None = None,
        language: str | None = None,
    ) -> dict[str, Any]:
        root = self._call(
            "modifyPromptTTS",
            _object_xml(
                "prompt",
                {
                    "description": description,
                    "name": prompt_name,
                    "type": "TTSGenerated",
                },
            )
            + _object_xml(
                "ttsInfo",
                {
                    "language": language,
                    "text": text,
                    "voice": voice,
                },
            ),
        )
        return _write_result(root)

    def modify_inbound_campaign(
        self,
        campaign_name: str,
        description: str | None = None,
        max_num_of_lines: int | None = None,
    ) -> dict[str, Any]:
        root = self._call(
            "modifyInboundCampaign",
            _object_xml(
                "campaign",
                {
                    "description": description,
                    "maxNumOfLines": max_num_of_lines,
                    "name": campaign_name,
                },
            ),
        )
        return _write_result(root)

    def delete_skill(self, skill_name: str) -> dict[str, Any]:
        root = self._call("deleteSkill", _element("skillName", skill_name))
        return _write_result(root)

    def delete_disposition(self, disposition_name: str) -> dict[str, Any]:
        root = self._call("removeDisposition", _element("dispositionName", disposition_name))
        return _write_result(root)

    def delete_prompt(self, prompt_name: str) -> dict[str, Any]:
        root = self._call("deletePrompt", _element("promptName", prompt_name))
        return _write_result(root)

    def delete_campaign(self, campaign_name: str) -> dict[str, Any]:
        root = self._call("deleteCampaign", _element("campaignName", campaign_name))
        return _write_result(root)

    def remove_dnis_from_campaign(
        self,
        campaign_name: str,
        dnis: list[str],
    ) -> dict[str, Any]:
        root = self._call(
            "removeDNISFromCampaign",
            _element("campaignName", campaign_name)
            + _repeated_elements("DNISList", dnis),
        )
        return _write_result(root)

    def remove_skills_from_campaign(
        self,
        campaign_name: str,
        skills: list[str],
    ) -> dict[str, Any]:
        root = self._call(
            "removeSkillsFromCampaign",
            _element("campaignName", campaign_name)
            + _repeated_elements("skills", skills),
        )
        return _write_result(root)

    def remove_dispositions_from_campaign(
        self,
        campaign_name: str,
        dispositions: list[str],
    ) -> dict[str, Any]:
        root = self._call(
            "removeDispositionsFromCampaign",
            _element("campaignName", campaign_name)
            + _repeated_elements("dispositions", dispositions),
        )
        return _write_result(root)

    def _call(self, method: str, inner_xml: str) -> etree._Element:
        body = _envelope(method, inner_xml)
        response = self._session.post(
            self._url,
            data=body.encode("utf-8"),
            timeout=self._timeout,
        )
        try:
            root = etree.fromstring(response.content)
        except etree.XMLSyntaxError:
            if hasattr(response, "raise_for_status"):
                response.raise_for_status()
            raise

        fault = _soap_fault(root)
        if fault:
            raise RuntimeError(fault)

        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        return root


def _esc(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _element(name: str, value: Any) -> str:
    if isinstance(value, bool):
        value = _bool_text(value)
    return f"<{name}>{_esc(value)}</{name}>"


def _optional_element(name: str, value: Any | None) -> str:
    if value is None or value == "":
        return ""
    return _element(name, value)


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


class _raw(str):
    pass


def _object_xml(name: str, fields: dict[str, Any]) -> str:
    inner = ""
    for key, value in fields.items():
        if value is None or value == "":
            continue
        if isinstance(value, _raw):
            inner += str(value)
        elif isinstance(value, dict):
            inner += _object_xml(key, value)
        elif isinstance(value, (list, tuple)):
            inner += _repeated_elements(key, value)
        else:
            inner += _element(key, value)
    return f"<{name}>{inner}</{name}>"


def _repeated_elements(name: str, values: list[Any] | tuple[Any, ...]) -> str:
    return "".join(_element(name, value) for value in values)


def _script_params_xml(params: dict[str, Any]) -> str:
    return "".join(
        _object_xml("params", {"name": key, "value": value})
        for key, value in params.items()
        if value is not None
    )


def _write_result(root: etree._Element) -> dict[str, Any]:
    items = _response_items(root, ("return",))
    if len(items) == 1 and isinstance(items[0], dict):
        return items[0]
    if items:
        return {"return": items}
    return {"status": "executed"}


def _envelope(method: str, inner_xml: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:ser="{SER_NS}">'
        "<soapenv:Header/>"
        "<soapenv:Body>"
        f"<ser:{method}>{inner_xml}</ser:{method}>"
        "</soapenv:Body>"
        "</soapenv:Envelope>"
    )


def _soap_fault(root: etree._Element) -> str | None:
    fault = root.find(f".//{{{SOAP_NS}}}Fault")
    if fault is None:
        fault = root.find(".//Fault")
    if fault is None:
        return None
    return (
        fault.findtext("faultstring")
        or fault.findtext("message")
        or "SOAP fault"
    )


def _response_items(
    root: etree._Element,
    item_tags: tuple[str, ...],
) -> list[Any]:
    items: list[Any] = []
    for element in root.iter():
        if _local_name(element.tag) in item_tags:
            items.append(_element_value(element))
    return items


def _element_value(element: etree._Element) -> Any:
    children = [child for child in element if isinstance(child.tag, str)]
    if not children:
        return (element.text or "").strip()

    result: dict[str, Any] = {}
    for child in children:
        key = _local_name(child.tag)
        value = _element_value(child)
        if key in result:
            if not isinstance(result[key], list):
                result[key] = [result[key]]
            result[key].append(value)
        else:
            result[key] = value
    return result


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


__all__ = [
    "Five9ConfigClient",
    "Five9Credentials",
]
