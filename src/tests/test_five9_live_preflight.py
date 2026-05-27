import importlib
import sys
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def soap_response(inner_xml):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>
    {inner_xml}
  </soapenv:Body>
</soapenv:Envelope>"""


class FakeResponse:
    def __init__(self, content, status_code=200):
        self.content = content.encode("utf-8")
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}
        self.auth = None

    def post(self, url, data, timeout):
        self.calls.append(
            {
                "url": url,
                "data": data.decode("utf-8"),
                "timeout": timeout,
            }
        )
        return FakeResponse(self.responses.pop(0))


class FakePreflightClient:
    def __init__(self):
        self.calls = []

    def get_skills(self, name_pattern=None):
        self.calls.append(("get_skills", name_pattern))
        return [{"name": "English", "description": "Live skill"}]

    def get_dispositions(self, name_pattern=None):
        self.calls.append(("get_dispositions", name_pattern))
        return [{"name": "Sale Completed"}]

    def get_prompts(self):
        self.calls.append(("get_prompts", None))
        return [{"name": "Main Greeting"}]

    def get_campaigns(self, name_pattern=None, campaign_type=None):
        self.calls.append(("get_campaigns", name_pattern, campaign_type))
        return [{"name": "Acme Main Inbound", "type": "inbound"}]

    def get_dnis_list(self, select_unassigned=False):
        self.calls.append(("get_dnis_list", select_unassigned))
        return ["800-555-0100"]

    def get_campaign_dnis_list(self, campaign_name):
        self.calls.append(("get_campaign_dnis_list", campaign_name))
        return ["800-555-0100"]


class Five9LivePreflightGateTests(unittest.TestCase):
    def setUp(self):
        self.preflight = importlib.import_module("src.tools.Five9.preflight")

    def test_live_mode_requires_explicit_approval(self):
        with self.assertRaises(PermissionError):
            self.preflight.five9_get_skills(
                mode="live",
                client=FakePreflightClient(),
            )

    def test_live_mode_requires_client(self):
        with self.assertRaises(ValueError):
            self.preflight.five9_get_skills(mode="live", approved=True)

    def test_live_mode_wraps_client_data_without_using_stub_inventory(self):
        client = FakePreflightClient()

        result = self.preflight.five9_get_skills(
            name_pattern="Eng.*",
            mode="live",
            approved=True,
            client=client,
        )

        self.assertEqual(result["tool_name"], "five9_get_skills")
        self.assertEqual(result["params"], {"name_pattern": "Eng.*"})
        datetime.fromisoformat(result["timestamp"])
        self.assertEqual(result["mode"], "live")
        self.assertEqual(result["result"], "success")
        self.assertEqual(result["data"], [{"name": "English", "description": "Live skill"}])
        self.assertEqual(client.calls, [("get_skills", "Eng.*")])

    def test_live_dnis_results_are_normalized_for_tool_contract(self):
        client = FakePreflightClient()

        dnis = self.preflight.five9_get_dnis_list(
            mode="live",
            approved=True,
            client=client,
        )["data"]
        campaign_dnis = self.preflight.five9_get_campaign_dnis_list(
            "Acme Main Inbound",
            mode="live",
            approved=True,
            client=client,
        )["data"]

        self.assertEqual(dnis, [{"number": "800-555-0100", "assigned_campaign": None}])
        self.assertEqual(
            campaign_dnis,
            [{"number": "800-555-0100", "assigned_campaign": "Acme Main Inbound"}],
        )


class Five9ConfigSoapClientTests(unittest.TestCase):
    def setUp(self):
        self.soap_client = importlib.import_module("src.tools.Five9.soap_client")

    def test_get_skills_posts_raw_soap_and_parses_return_objects(self):
        session = FakeSession(
            [
                soap_response(
                    """
<ns2:getSkillsResponse xmlns:ns2="http://service.admin.ws.five9.com/">
  <return>
    <name>English</name>
    <description>Live English skill</description>
  </return>
</ns2:getSkillsResponse>
"""
                )
            ]
        )
        client = self.soap_client.Five9ConfigClient(
            username="user",
            password="pass",
            domain="api.five9.test",
            session=session,
        )

        data = client.get_skills("Eng.*")

        self.assertEqual(data, [{"name": "English", "description": "Live English skill"}])
        self.assertEqual(
            session.calls[0]["url"],
            "https://api.five9.test/wsadmin/v13/AdminWebService",
        )
        self.assertIn("<ser:getSkills>", session.calls[0]["data"])
        self.assertIn("<skillNamePattern>Eng.*</skillNamePattern>", session.calls[0]["data"])
        self.assertIn("</ser:getSkills>", session.calls[0]["data"])
        self.assertEqual(session.calls[0]["timeout"], 60)

    def test_client_escapes_xml_parameters(self):
        session = FakeSession(
            [
                soap_response(
                    """
<ns2:getCampaignsResponse xmlns:ns2="http://service.admin.ws.five9.com/">
  <return><name>A&amp;B Campaign</name><mode>BASIC</mode></return>
</ns2:getCampaignsResponse>
"""
                )
            ]
        )
        client = self.soap_client.Five9ConfigClient(
            username="user",
            password="pass",
            session=session,
        )

        data = client.get_campaigns("A&B", "inbound")

        self.assertEqual(data, [{"name": "A&B Campaign", "mode": "BASIC"}])
        self.assertIn("<campaignNamePattern>A&amp;B</campaignNamePattern>", session.calls[0]["data"])
        self.assertIn("<campaignType>inbound</campaignType>", session.calls[0]["data"])

    def test_scalar_return_values_are_parsed_for_dnis_reads(self):
        session = FakeSession(
            [
                soap_response(
                    """
<ns2:getCampaignDNISListResponse xmlns:ns2="http://service.admin.ws.five9.com/">
  <return>800-555-0100</return>
  <return>800-555-0101</return>
</ns2:getCampaignDNISListResponse>
"""
                )
            ]
        )
        client = self.soap_client.Five9ConfigClient(
            username="user",
            password="pass",
            session=session,
        )

        data = client.get_campaign_dnis_list("Acme Main Inbound")

        self.assertEqual(data, ["800-555-0100", "800-555-0101"])
        self.assertIn("<campaignName>Acme Main Inbound</campaignName>", session.calls[0]["data"])

    def test_prompt_response_with_prompts_elements_is_parsed(self):
        session = FakeSession(
            [
                soap_response(
                    """
<ns2:getPromptsResponse xmlns:ns2="http://service.admin.ws.five9.com/">
  <prompts>
    <name>Main Greeting</name>
    <description>Live prompt</description>
  </prompts>
</ns2:getPromptsResponse>
"""
                )
            ]
        )
        client = self.soap_client.Five9ConfigClient(
            username="user",
            password="pass",
            session=session,
        )

        data = client.get_prompts()

        self.assertEqual(data, [{"name": "Main Greeting", "description": "Live prompt"}])
        self.assertIn("<ser:getPrompts>", session.calls[0]["data"])

    def test_soap_fault_raises_runtime_error(self):
        session = FakeSession(
            [
                soap_response(
                    """
<soapenv:Fault xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <faultstring>Invalid credentials</faultstring>
</soapenv:Fault>
"""
                )
            ]
        )
        client = self.soap_client.Five9ConfigClient(
            username="user",
            password="pass",
            session=session,
        )

        with self.assertRaisesRegex(RuntimeError, "Invalid credentials"):
            client.get_prompts()

    def test_http_500_soap_fault_raises_fault_message(self):
        session = FakeSession(
            [
                soap_response(
                    """
<soapenv:Fault xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <faultstring>Campaign not found</faultstring>
</soapenv:Fault>
"""
                )
            ]
        )
        session.responses = [session.responses[0]]

        original_post = session.post

        def post_with_500(url, data, timeout):
            response = original_post(url, data, timeout)
            response.status_code = 500
            return response

        session.post = post_with_500
        client = self.soap_client.Five9ConfigClient(
            username="user",
            password="pass",
            session=session,
        )

        with self.assertRaisesRegex(RuntimeError, "Campaign not found"):
            client.get_campaign_dnis_list("Missing Campaign")


if __name__ == "__main__":
    unittest.main()
