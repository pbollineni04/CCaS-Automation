# Five9 Tool Packs and Sprint 1 Preflight Spec

Last updated: 2026-05-11

## Objective

Build the Five9 tool roadmap in packs, then implement Sprint 1 only: a production-capable Read/Preflight Pack. The preflight pack lets the planner inspect Five9 state before proposing create, modify, delete, or rollback actions.

Sprint 1 supports live Five9 SOAP reads behind explicit approval and an injected client. Stub/offline mode remains available for tests, demos, and local development. Sprint 1 must not load `.env`, call writes, use Supabase, or touch the working Phase 1 prompt uploader.

## Pack Roadmap

### Pack 1: Five9 Read/Preflight Pack

Purpose: collect current configuration state before planning writes.

Sprint 1 tools, implemented as real read operations with stub/offline fallback:

- `five9_get_skills`
- `five9_get_dispositions`
- `five9_get_prompts`
- `five9_get_campaigns`
- `five9_get_dnis_list`
- `five9_get_campaign_dnis_list`

Planner helper:

- Compare desired objects with preflight state.
- Return `exists`, `missing`, `conflicts`, and `recommended_action`.
- Recommend `skip` for existing desired objects, `create` for missing objects, and `review` when a DNIS is assigned to another campaign.

### Pack 2: Core Config Write Pack

Purpose: create the core configuration objects needed for the CEO demo and later Five9 setup flows.

Documented tools, not implemented in Sprint 1:

- `five9_create_skill`
- `five9_create_disposition`
- `five9_add_prompt_tts`
- `five9_create_inbound_campaign`
- `five9_add_dnis_to_campaign`
- `five9_add_skills_to_campaign`
- `five9_add_dispositions_to_campaign`
- `five9_set_default_ivr_schedule`

### Pack 3: Modify/Delete/Rollback Pack

Purpose: support controlled changes after initial creation and provide rollback-oriented primitives.

Documented capabilities, not implemented in Sprint 1:

- Modify and delete skills.
- Modify and delete dispositions.
- Modify and delete prompts.
- Modify and delete inbound campaigns.
- Remove DNIS from campaign.
- Remove skills from campaign.
- Remove dispositions from campaign.
- Capture pre-change state before writes so rollback plans can be generated.

### Pack 4: IVR Script Management Pack

Purpose: manage IVR scripts after read, write, modify, delete, and rollback primitives exist.

Documented tools, intentionally deferred until after the rollback pack:

- `five9_get_ivr_scripts`
- `five9_create_ivr_script`
- `five9_modify_ivr_script`
- `five9_delete_ivr_script`

## Sprint 1 Implementation Scope

Add:

- `src/tools/Five9/soap_client.py` for the production raw SOAP v13 read client.
- `src/tools/Five9/preflight.py` for tool wrappers, stub/offline data, approval gates, and comparison helpers.

`soap_client.py` uses the same raw SOAP pattern as Phase 1 prompt upload:

- `requests`
- `lxml`
- no `zeep`
- endpoint `https://{domain}/wsadmin/v13/AdminWebService`
- namespace `http://service.admin.ws.five9.com/`

`preflight.py` includes:

- A shared tool result helper.
- Deterministic in-memory Five9 sample inventory for `mode="stub"`.
- The six read/preflight tools listed in Pack 1.
- A comparison helper for planner-facing preflight decisions.
- A live-mode gate requiring `approved=True` and an injected Five9 client.

Each Sprint 1 tool returns:

```json
{
  "tool_name": "five9_get_skills",
  "params": {},
  "timestamp": "server-side ISO 8601 local time",
  "mode": "stub | live",
  "result": "success",
  "data": []
}
```

Filtering requirements:

- Skills, dispositions, prompts, and campaigns support name-pattern filtering.
- Campaign reads may also filter by campaign type.
- DNIS reads can return all sample DNIS values or only unassigned DNIS values.
- Campaign DNIS reads filter by campaign name.

Live mode requirements:

- Caller passes `mode="live"`.
- Caller passes `approved=True`.
- Caller passes a configured `Five9ConfigClient`.
- Missing approval returns `PermissionError`.
- Missing client returns `ValueError`.
- Live mode performs reads only.

## API Source Notes

The extracted Five9 Configuration Web Services text is in:

`planning/api-research/five9/extracted/Configuration Web Services API_2026-05-05 10.06.txt`

Relevant method groups:

- Campaign Configuration: `getCampaigns`, `getDNISList`, `getCampaignDNISList`, `createInboundCampaign`, `addDNISToCampaign`, `addSkillsToCampaign`
- Prompt Management: `getPrompts`, `addPromptTTS`
- Skill Management: `getSkills`, `createSkill`
- IVR Script Management: `getIVRScripts`, `createIVRScript`, `modifyIVRScript`, `deleteIVRScript`

Five9 queues remain represented as skills and campaign routing concepts until live API research proves a separate queue object is required.

## Out of Scope for Sprint 1

- Live Five9 write calls.
- Five9 `.env` reads.
- Supabase persistence.
- Zoom Contact Center.
- CXone.
- Core config write tools.
- Modify, delete, or rollback tools.
- IVR script tools.
- Changes to the working Phase 1 prompt uploader.

## Test Plan

Add `src/tests/test_five9_preflight.py` covering:

- Every Sprint 1 read tool returns `mode: "stub"`, a timestamp, the correct tool name, and deterministic data.
- Name-pattern or campaign-name filters work where applicable.
- Preflight code does not import or call the live Five9 prompt client.
- Existing skill, disposition, prompt, campaign, and DNIS recommend `skip`.
- Missing objects recommend `create`.
- DNIS assigned to another campaign recommends `review`.
- One stub result is returned per tool call.

Add `src/tests/test_five9_live_preflight.py` covering:

- Live mode requires explicit approval.
- Live mode requires an injected client.
- Live mode wraps client data in the standard tool result envelope.
- Raw SOAP envelopes are posted to the Five9 v13 admin endpoint.
- SOAP parameters are XML-escaped.
- SOAP response objects and scalar DNIS lists are parsed.
- SOAP faults raise `RuntimeError`.

Run:

```powershell
py -m unittest discover src/tests -v
```

## Acceptance Criteria

- `src/tools/Five9/soap_client.py` provides production raw SOAP read calls for Sprint 1 preflight methods.
- `src/tools/Five9/preflight.py` provides deterministic stub/offline reads and gated live reads.
- The planner-facing comparison helper returns `exists`, `missing`, `conflicts`, and `recommended_action`.
- Sprint 1 tests pass without importing or changing the Phase 1 prompt client.
- Existing Phase 1 prompt upload files remain unchanged.
- Core writes, rollback, and IVR script management are documented but not implemented.
