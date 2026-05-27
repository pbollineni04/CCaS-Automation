import importlib
import sys
import unittest
from pathlib import Path

from src.tests.test_five9_live_preflight import FakeSession, soap_response


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


EMPTY_RESPONSE = soap_response("<ns2:ok xmlns:ns2=\"http://service.admin.ws.five9.com/\"/>")


class Five9ConfigSoapModifyTests(unittest.TestCase):
    def setUp(self):
        self.soap_client = importlib.import_module("src.tools.Five9.soap_client")

    def _client_with_session(self):
        session = FakeSession([EMPTY_RESPONSE])
        client = self.soap_client.Five9ConfigClient(
            username="user",
            password="pass",
            domain="api.five9.test",
            session=session,
        )
        return client, session

    def test_modify_skill_posts_skill_object(self):
        client, session = self._client_with_session()

        client.modify_skill(skill_name="ZZ_TEST_Codex_DeleteMe", description="Updated")

        body = session.calls[0]["data"]
        self.assertIn("<ser:modifySkill>", body)
        self.assertIn("<skill>", body)
        self.assertIn("<name>ZZ_TEST_Codex_DeleteMe</name>", body)
        self.assertIn("<description>Updated</description>", body)

    def test_modify_disposition_posts_disposition_object(self):
        client, session = self._client_with_session()

        client.modify_disposition(name="Follow Up Required", description="Updated")

        body = session.calls[0]["data"]
        self.assertIn("<ser:modifyDisposition>", body)
        self.assertIn("<disposition>", body)
        self.assertIn("<name>Follow Up Required</name>", body)
        self.assertIn("<description>Updated</description>", body)

    def test_modify_prompt_tts_posts_prompt_and_tts_info(self):
        client, session = self._client_with_session()

        client.modify_prompt_tts(prompt_name="Main Greeting", text="Updated greeting", voice="Terry")

        body = session.calls[0]["data"]
        self.assertIn("<ser:modifyPromptTTS>", body)
        self.assertIn("<prompt>", body)
        self.assertIn("<name>Main Greeting</name>", body)
        self.assertIn("<type>TTSGenerated</type>", body)
        self.assertIn("<ttsInfo>", body)
        self.assertIn("<text>Updated greeting</text>", body)
        self.assertIn("<voice>Terry</voice>", body)

    def test_modify_inbound_campaign_posts_campaign_object(self):
        client, session = self._client_with_session()

        client.modify_inbound_campaign(
            campaign_name="Acme Main Inbound",
            description="Updated campaign",
            max_num_of_lines=4,
        )

        body = session.calls[0]["data"]
        self.assertIn("<ser:modifyInboundCampaign>", body)
        self.assertIn("<campaign>", body)
        self.assertIn("<name>Acme Main Inbound</name>", body)
        self.assertIn("<description>Updated campaign</description>", body)
        self.assertIn("<maxNumOfLines>4</maxNumOfLines>", body)


if __name__ == "__main__":
    unittest.main()
