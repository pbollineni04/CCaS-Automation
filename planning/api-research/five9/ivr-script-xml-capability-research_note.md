# Five9 IVR Script XML Capability Research Note

Date: 2026-05-11

## Question

What can the CCaaS Automation Agent safely do with Five9 IVR scripts through the Configuration Web Services API, and what still needs discovery before we generate IVR logic?

## Confirmed API Surface

The Five9 Configuration Web Services API exposes IVR script management through these SOAP methods:

- `getIVRScripts(namePattern)`
- `createIVRScript(name)`
- `modifyIVRScript(scriptDef)`
- `deleteIVRScript(name)`

The relevant data type is `ivrScriptDef`, which contains:

- `name`
- `description`
- `xmlDefinition`

The API documentation describes `xmlDefinition` as the script in XML format. It may be supplied as CDATA or escaped XML text. This means the API can read and write the serialized IVR definition, but it does not document a stable high-level builder schema for menu nodes, branches, prompt nodes, transfer nodes, or layout.

## Confirmed Campaign Relationship

Five9 campaign documentation says IVR schedules associate IVR and Visual IVR scripts with inbound and autodial campaigns. IVR scripts are required for inbound campaigns and are responsible for custom greetings, prompts, instructions, and call routing.

The API data type `ivrScriptSchedule` connects a campaign schedule to:

- `scriptName`
- optional `scriptParameters` for foreign script modules

The local API documentation notes that when setting this through `createInboundCampaign`, only the default IVR schedule can be set or modified through the API.

## External Tooling Evidence

The public `PSFive9Admin` PowerShell module updates an IVR script by constructing an `ivrScriptDef`, setting `name`, optionally setting `description`, optionally setting `xmlDefinition`, and calling `modifyIVRScript`. Its examples copy XML from one script to another or load XML from a file before update.

This supports our implementation direction: raw XML read/write is a real Five9 automation path, but generation must be treated carefully because the XML structure is Five9-internal.

## Local Java App Evidence

The Five9 Admin Java application cache includes IVR editor packages under `com/five9/cc/ui/ivr`, including modules for:

- `menu`
- `play`
- `getdigits`
- `skilltransfer`
- `campaigntransfer`
- `voicemailtransfer`
- `ifelse`
- `foreignscript`

This supports the assumption that the visual editor serializes a graph of IVR modules into `xmlDefinition`.

## Export Inspection

The file `C:\Users\jrgoo\Desktop\New Text Document (2).txt` contains 34 IVR script definitions returned as JSON with `description`, `name`, and `xmlDefinition`.

Useful scripts for compiler discovery:

- `GenericTest`: small voice-flow candidate with `incomingCall`, `setVariable`, `menu`, `play`, `skillTransfer`, and `hangup`.
- `Priority Test`: menu branches to different skill transfers with priority-setting variables.
- `ItsTheFeds`: simple menu-to-variable-to-skill-transfer pattern.
- `TransferTest`: adds `input` and `thirdPartyTransfer` behavior.
- `VIVR QCB`: small queue-callback style script with `skillTransfer` details.

Less useful as first compiler fixtures:

- `SFDC Einstein`, `Five9 NLP`, Rules Engine, and email/chat examples. These are valid references but too integration-heavy for the first voice IVR compiler.

## XML Model Observations

Every inspected script follows the same broad shape:

```xml
<ivrScript>
  <domainId>...</domainId>
  <properties/>
  <modules>...</modules>
  <modulesOnHangup>...</modulesOnHangup>
  <userVariables>...</userVariables>
  <multiLanguagesPrompts>...</multiLanguagesPrompts>
  ...
  <version>...</version>
</ivrScript>
```

Module graph behavior is represented by:

- module tag name, such as `incomingCall`, `menu`, `play`, `skillTransfer`, `hangup`
- `moduleId`
- `moduleName`
- `ascendants`
- `singleDescendant`
- sometimes `exceptionalDescendant`
- branch maps inside `menu`, `case`, and `ifElse` modules

The graph should be parsed by module IDs, not by screen coordinates or display names.

## Practical Capability Boundary

Safe now:

- List IVR scripts by name pattern.
- Read one or all `xmlDefinition` values.
- Summarize scripts into modules, branches, variables, prompts, and transfer destinations.
- Store sanitized XML fixtures.
- Dry-run raw XML create/modify/delete plans.
- Live raw XML update only with explicit approval and a known disposable target.

Not safe yet:

- Generate arbitrary production IVR XML from scratch.
- Modify production IVR XML without preflight diff, backup, and rollback.
- Assume the XML schema is stable without fixture tests.
- Treat visual layout fields as behavior.
- Generate integration-heavy modules like `query`, `foreignScript`, NLP, Salesforce, or callback flows in the first compiler.

## Recommended Build Path

1. Build an IVR XML parser/summarizer first.
   - Input: `xmlDefinition`
   - Output: script summary with modules, edges, branch labels, prompt references, transfer targets, and variables.

2. Add a fixture capture workflow.
   - Read `GenericTest` or a new `ZZ_TEST_Codex_IVR_Source`.
   - Save sanitized XML under tests/fixtures.
   - Redact domain IDs, real skill names, phone numbers, URLs, and customer-specific strings if needed.

3. Build a constrained compiler only after fixture capture.
   - Supported first shape: incoming call -> greeting/play -> menu -> skill transfer branches -> no-match/no-input -> hangup.
   - Do not support business hours, foreign scripts, NLP, Salesforce, callbacks, or external HTTP queries in v1.

4. Add approval-gated raw XML update.
   - Always read current XML first.
   - Generate a diff summary.
   - Require explicit approval.
   - Keep a rollback copy of the prior `xmlDefinition`.

5. Later, add IVR schedules to campaign configuration.
   - Separate script body management from campaign schedule assignment.
   - Only default schedule modification is known to be API-supported from current docs.

## Build Recommendation

The next implementation should not be a full IVR builder. It should be an IVR XML parser and discovery viewer. That gives the agent a reliable read model before it writes. After that, implement a very narrow compiler for simple menu routing and prove it against a disposable Five9 IVR script.
