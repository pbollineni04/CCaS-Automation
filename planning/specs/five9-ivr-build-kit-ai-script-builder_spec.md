# Five9 IVR Build Kit + AI-Usable Script Builder Spec

Date: 2026-05-11

## Summary

Build IVR script generation around a shared Five9 IVR Build Kit. The UI and AI use the same normalized build-plan schema, module catalog, validation rules, and compiler. The AI does not write raw Five9 XML directly in v1; it proposes a build plan and the compiler generates `xmlDefinition`.

## V1 Capability

V1 supports a simple inbound menu IVR:

```text
Incoming Call -> Greeting -> Menu
Menu option -> Skill or Campaign Transfer
No Match / No Input -> Hangup
```

Supported generated module blocks:

- `incomingCall`
- `play`
- `menu`
- `skillTransfer`
- `campaignTransfer`
- `hangup`

Parsed but not generated in v1:

- `setVariable`
- `case`
- `ifElse`
- `query`
- `foreignScript`
- `input`
- `thirdPartyTransfer`
- `voicemailTransfer`

## AI Contract

The AI must produce normalized build-plan JSON, not raw XML:

```json
{
  "script_name": "Acme Main IVR",
  "description": "Main inbound IVR",
  "greeting": {
    "prompt_name": "Main Greeting",
    "text": "Thank you for calling Acme Health Services."
  },
  "menu": {
    "name": "Main Menu",
    "options": [
      { "digit": "1", "label": "Sales", "transfer_type": "skill", "target": "Sales" },
      { "digit": "2", "label": "Billing", "transfer_type": "skill", "target": "Billing" },
      { "digit": "3", "label": "Support", "transfer_type": "skill", "target": "Support" }
    ],
    "no_match": "hangup",
    "no_input": "hangup"
  }
}
```

The backend validates the plan, returns preflight requirements, and rejects duplicate digits, unsupported transfer types, empty targets, and raw module/XML requests.

## Public Interfaces

- `GET /api/run/five9/ivr-builder/catalog`
- `POST /api/run/five9/ivr-builder/analyze-file`
- `POST /api/run/five9/ivr-builder/validate-plan`
- `POST /api/run/five9/ivr-builder/compile`
- `POST /api/run/five9/ivr-builder/deploy`

Live deploy uses the existing Five9 IVR script approval gate and executes only `five9_modify_ivr_script` with explicit approval and credentials.

## UI

The UI exposes `Five9 -> IVR Scripts -> Script Builder` and shows:

```text
Requirements -> Build Plan -> Module Manual -> Generated XML -> Approval -> Five9 Update
```

It can analyze local `.five9ivr` XML, display the module manual, validate build plans, compile XML, copy/export `.five9ivr`, and dry-run or approval-gate live deployment.

## Safety

- No live update runs without explicit approval.
- V1 does not support full freeform IVR editing.
- Generated XML is constrained to the supported simple menu shape.
- Business hours, callbacks, NLP, Salesforce, external HTTP queries, foreign scripts, and advanced variable logic remain future compiler work.
