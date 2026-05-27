# Five9 IVR Java App Research Note

Date: 2026-05-11

## Purpose

Use the Five9 Admin Java application as a second source of truth for how visual IVR logic is represented. The SOAP API exposes `ivrScriptDef.xmlDefinition`, and the local Java cache confirms the Admin app includes IVR editor modules that likely serialize visual call-flow objects into that XML definition.

## JNLP Evidence

- Local file inspected: `C:\Users\jrgoo\Downloads\domainAdmin.jnlp`
- JNLP codebase: `https://webstorage08.five9.com`
- Main launcher class: `com.five9.ual.launcher.LaunchManager`
- Referenced Admin launcher jar: `/13.0/start/lib/ual__V13.0.462__CERT1.0.0.jar`

## Cached Java App Evidence

Local Java cache inspection found Five9 Admin classes under:

- `com/five9/cc/ui/ivr`

Relevant IVR module packages found:

- `menu`
- `play`
- `getdigits`
- `skilltransfer`
- `campaigntransfer`
- `voicemailtransfer`
- `ifelse`
- `foreignscript`

## API Connection

The Five9 Configuration Web Services API exposes:

- `getIVRScripts(namePattern)` returning `ivrScriptDef`
- `createIVRScript(name)`
- `modifyIVRScript(scriptDef)`
- `deleteIVRScript(name)`

`ivrScriptDef` includes:

- `name`
- `description`
- `xmlDefinition`

The API documentation describes `xmlDefinition` as the script in XML format, either as CDATA or escaped XML text.

## Implementation Decision

The first IVR pack reads and writes raw `xmlDefinition` only. It does not yet generate IVR logic.

The next discovery step is:

1. Manually create `ZZ_TEST_Codex_IVR_Source` in Five9 Admin.
2. Add a minimal flow: incoming call, greeting, menu options 1/2/3, and distinct test destinations.
3. Use the UI IVR XML Discovery view to live-read the script by name.
4. Save a sanitized XML fixture.
5. Build the first constrained compiler from requirements to simple menu IVR XML using only modules proven by the fixture and Java package evidence.

## Safety

No Java app launching or reverse-engineering is required for this phase. No live IVR create, modify, or delete operation should be executed during implementation or automated tests.
