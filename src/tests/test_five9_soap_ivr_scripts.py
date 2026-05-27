import importlib
import sys
import unittest
from pathlib import Path

from src.tests.test_five9_live_preflight import FakeSession, soap_response


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


EMPTY_RESPONSE = soap_response("<ns2:ok xmlns:ns2=\"http://service.admin.ws.five9.com/\"/>")
IVR_RESPONSE = soap_response(
    """
    <ns2:getIVRScriptsResponse xmlns:ns2="http://service.admin.ws.five9.com/">
      <return>
        <name>ZZ_TEST_Codex_IVR_Source</name>
        <description>Source IVR</description>
        <xmlDefinition>&lt;ivr-script&gt;&lt;module type="menu"/&gt;&lt;/ivr-script&gt;</xmlDefinition>
      </return>
    </ns2:getIVRScriptsResponse>
    """
)


class Five9ConfigSoapIvrScriptTests(unittest.TestCase):
    def setUp(self):
        self.soap_client = importlib.import_module("src.tools.Five9.soap_client")

    def _client_with_session(self, response=EMPTY_RESPONSE):
        session = FakeSession([response])
        client = self.soap_client.Five9ConfigClient(
            username="user",
            password="pass",
            domain="api.five9.test",
            session=session,
        )
        return client, session

    def test_get_ivr_scripts_posts_optional_name_pattern_and_parses_xml_definition(self):
        client, session = self._client_with_session(IVR_RESPONSE)

        result = client.get_ivr_scripts(name_pattern="ZZ_TEST")

        body = session.calls[0]["data"]
        self.assertIn("<ser:getIVRScripts>", body)
        self.assertIn("<namePattern>ZZ_TEST</namePattern>", body)
        self.assertEqual(result[0]["name"], "ZZ_TEST_Codex_IVR_Source")
        self.assertIn("<ivr-script>", result[0]["xmlDefinition"])

    def test_create_ivr_script_posts_name(self):
        client, session = self._client_with_session()

        client.create_ivr_script(name="ZZ_TEST_Codex_IVR")

        body = session.calls[0]["data"]
        self.assertIn("<ser:createIVRScript>", body)
        self.assertIn("<name>ZZ_TEST_Codex_IVR</name>", body)

    def test_modify_ivr_script_posts_script_def_with_xml_definition(self):
        client, session = self._client_with_session()

        client.modify_ivr_script(
            name="ZZ_TEST_Codex_IVR",
            description="Updated IVR",
            xml_definition="<ivr-script><module type=\"menu\"/></ivr-script>",
        )

        body = session.calls[0]["data"]
        self.assertIn("<ser:modifyIVRScript>", body)
        self.assertIn("<scriptDef>", body)
        self.assertIn("<name>ZZ_TEST_Codex_IVR</name>", body)
        self.assertIn("<description>Updated IVR</description>", body)
        self.assertIn("&lt;ivr-script&gt;", body)
        self.assertIn("type=&quot;menu&quot;", body)
        self.assertIn("&lt;/ivr-script&gt;", body)

    def test_delete_ivr_script_posts_name(self):
        client, session = self._client_with_session()

        client.delete_ivr_script(name="ZZ_TEST_Codex_IVR")

        body = session.calls[0]["data"]
        self.assertIn("<ser:deleteIVRScript>", body)
        self.assertIn("<name>ZZ_TEST_Codex_IVR</name>", body)


if __name__ == "__main__":
    unittest.main()
