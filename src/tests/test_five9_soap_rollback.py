import importlib
import sys
import unittest
from pathlib import Path

from src.tests.test_five9_live_preflight import FakeSession, soap_response


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


EMPTY_RESPONSE = soap_response("<ns2:ok xmlns:ns2=\"http://service.admin.ws.five9.com/\"/>")


class Five9ConfigSoapRollbackTests(unittest.TestCase):
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

    def test_delete_skill_posts_skill_name(self):
        client, session = self._client_with_session()

        result = client.delete_skill(skill_name="ZZ_TEST_Codex_DeleteMe")

        body = session.calls[0]["data"]
        self.assertEqual(result, {"status": "executed"})
        self.assertIn("<ser:deleteSkill>", body)
        self.assertIn("<skillName>ZZ_TEST_Codex_DeleteMe</skillName>", body)

    def test_delete_disposition_posts_disposition_name(self):
        client, session = self._client_with_session()

        client.delete_disposition(disposition_name="ZZ Test Disposition")

        body = session.calls[0]["data"]
        self.assertIn("<ser:removeDisposition>", body)
        self.assertIn("<dispositionName>ZZ Test Disposition</dispositionName>", body)

    def test_delete_prompt_posts_prompt_name(self):
        client, session = self._client_with_session()

        client.delete_prompt(prompt_name="ZZ Test Prompt")

        body = session.calls[0]["data"]
        self.assertIn("<ser:deletePrompt>", body)
        self.assertIn("<promptName>ZZ Test Prompt</promptName>", body)

    def test_delete_campaign_posts_campaign_name(self):
        client, session = self._client_with_session()

        client.delete_campaign(campaign_name="ZZ Test Campaign")

        body = session.calls[0]["data"]
        self.assertIn("<ser:deleteCampaign>", body)
        self.assertIn("<campaignName>ZZ Test Campaign</campaignName>", body)

    def test_remove_dnis_skills_and_dispositions_post_repeated_values(self):
        client, session = self._client_with_session()
        client.remove_dnis_from_campaign(
            campaign_name="Acme Main Inbound",
            dnis=["800-555-0100", "800-555-0101"],
        )
        dnis_body = session.calls[0]["data"]

        client, session = self._client_with_session()
        client.remove_skills_from_campaign(
            campaign_name="Acme Main Inbound",
            skills=["English", "Spanish"],
        )
        skills_body = session.calls[0]["data"]

        client, session = self._client_with_session()
        client.remove_dispositions_from_campaign(
            campaign_name="Acme Main Inbound",
            dispositions=["Sale Completed", "Follow Up Required"],
        )
        dispositions_body = session.calls[0]["data"]

        self.assertIn("<ser:removeDNISFromCampaign>", dnis_body)
        self.assertIn("<DNISList>800-555-0100</DNISList>", dnis_body)
        self.assertIn("<DNISList>800-555-0101</DNISList>", dnis_body)
        self.assertIn("<ser:removeSkillsFromCampaign>", skills_body)
        self.assertIn("<skills>English</skills>", skills_body)
        self.assertIn("<skills>Spanish</skills>", skills_body)
        self.assertIn("<ser:removeDispositionsFromCampaign>", dispositions_body)
        self.assertIn("<dispositions>Sale Completed</dispositions>", dispositions_body)
        self.assertIn("<dispositions>Follow Up Required</dispositions>", dispositions_body)


if __name__ == "__main__":
    unittest.main()
