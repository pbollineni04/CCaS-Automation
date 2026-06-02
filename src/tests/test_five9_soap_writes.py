import importlib
import sys
import unittest
from pathlib import Path

from src.tests.test_five9_live_preflight import FakeSession, soap_response


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


EMPTY_RESPONSE = soap_response("<ns2:ok xmlns:ns2=\"http://service.admin.ws.five9.com/\"/>")


class Five9ConfigSoapWriteTests(unittest.TestCase):
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

    def test_create_skill_posts_skill_info_object(self):
        client, session = self._client_with_session()

        result = client.create_skill(name="English", description="Language skill")

        body = session.calls[0]["data"]
        self.assertEqual(result, {"status": "executed"})
        self.assertIn("<ser:createSkill>", body)
        self.assertIn("<skillInfo>", body)
        self.assertIn("<skill>", body)
        self.assertIn("<name>English</name>", body)
        self.assertIn("<description>Language skill</description>", body)

    def test_create_disposition_posts_disposition_object(self):
        client, session = self._client_with_session()

        client.create_disposition(name="Sale Completed")

        body = session.calls[0]["data"]
        self.assertIn("<ser:createDisposition>", body)
        self.assertIn("<disposition>", body)
        self.assertIn("<name>Sale Completed</name>", body)

    def test_add_prompt_tts_posts_prompt_and_tts_info(self):
        client, session = self._client_with_session()

        client.add_prompt_tts(prompt_name="Main Greeting", text="Thank you.", voice="Terry")

        body = session.calls[0]["data"]
        self.assertIn("<ser:addPromptTTS>", body)
        self.assertIn("<prompt>", body)
        self.assertIn("<name>Main Greeting</name>", body)
        self.assertIn("<type>TTSGenerated</type>", body)
        self.assertIn("<ttsInfo>", body)
        self.assertIn("<text>Thank you.</text>", body)
        self.assertIn("<voice>Terry</voice>", body)

    def test_create_inbound_campaign_posts_campaign_object(self):
        client, session = self._client_with_session()

        client.create_inbound_campaign(
            campaign_name="Acme Main Inbound",
            default_ivr_script_name="Main IVR",
            description="Main inbound",
        )

        body = session.calls[0]["data"]
        self.assertIn("<ser:createInboundCampaign>", body)
        self.assertIn("<campaign>", body)
        self.assertIn(
            "<defaultIvrSchedule><ivrSchedule><scriptName>Main IVR</scriptName></ivrSchedule></defaultIvrSchedule>",
            body,
        )
        self.assertNotIn("<defaultIvrSchedule><name>", body)
        self.assertIn("<name>Acme Main Inbound</name>", body)
        self.assertIn("<description>Main inbound</description>", body)

    def test_add_dnis_to_campaign_posts_repeated_dnis_list_elements(self):
        client, session = self._client_with_session()

        client.add_dnis_to_campaign(campaign_name="Acme Main Inbound", dnis=["800-555-0100", "800-555-0101"])

        body = session.calls[0]["data"]
        self.assertIn("<ser:addDNISToCampaign>", body)
        self.assertIn("<campaignName>Acme Main Inbound</campaignName>", body)
        self.assertIn("<DNISList>800-555-0100</DNISList>", body)
        self.assertIn("<DNISList>800-555-0101</DNISList>", body)

    def test_add_skills_and_dispositions_post_repeated_values(self):
        client, session = self._client_with_session()
        client.add_skills_to_campaign(campaign_name="Acme Main Inbound", skills=["English", "Spanish"])
        skills_body = session.calls[0]["data"]

        client, session = self._client_with_session()
        client.add_dispositions_to_campaign(
            campaign_name="Acme Main Inbound",
            dispositions=["Sale Completed"],
            is_skip_preview_disposition=False,
        )
        dispositions_body = session.calls[0]["data"]

        self.assertIn("<ser:addSkillsToCampaign>", skills_body)
        self.assertIn("<skills>English</skills>", skills_body)
        self.assertIn("<skills>Spanish</skills>", skills_body)
        self.assertIn("<ser:addDispositionsToCampaign>", dispositions_body)
        self.assertIn("<dispositions>Sale Completed</dispositions>", dispositions_body)
        self.assertIn("<isSkipPreviewDisposition>false</isSkipPreviewDisposition>", dispositions_body)

    def test_set_default_ivr_schedule_posts_campaign_script_and_params(self):
        client, session = self._client_with_session()

        client.set_default_ivr_schedule(
            campaign_name="Acme Main Inbound",
            script_name="Main IVR",
            params={"timezone": "Eastern"},
            is_visual_mode_enabled=False,
        )

        body = session.calls[0]["data"]
        self.assertIn("<ser:setDefaultIVRSchedule>", body)
        self.assertIn("<campaignName>Acme Main Inbound</campaignName>", body)
        self.assertIn("<scriptName>Main IVR</scriptName>", body)
        self.assertIn("<params>", body)
        self.assertIn("<name>timezone</name>", body)
        self.assertIn("<value>Eastern</value>", body)
        self.assertIn("<isVisualModeEnabled>false</isVisualModeEnabled>", body)


if __name__ == "__main__":
    unittest.main()
