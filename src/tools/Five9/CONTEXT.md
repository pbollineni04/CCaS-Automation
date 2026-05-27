# Five9 Tools Workspace

Last updated: 2026-05-12

Five9 is the primary CCaaS platform for Phase 1, live configuration tooling, and IVR build/discovery work. This workspace contains the working prompt bulk upload tool, SOAP client code, approval-gated tool packs, and Five9-specific operation modules.

## Existing Phase 1

Working code:

- `Prompt_Management/Prompt_Bulk_Upload/five9_prompts.py` - raw SOAP prompt operations
- `Prompt_Management/Prompt_Bulk_Upload/bulk_upload.py` - CLI bulk upload entry point
- `Prompt_Management/Prompt_Bulk_Upload/sample_manifest.csv` - sample upload manifest

## Current Package Layout

- `common/` - shared SOAP client and write-result helpers
- `preflight_pack/` - read/preflight tools and comparison helpers
- `core_config/` - create/add/set configuration write tools
- `modify_config/` - modify/update configuration tools
- `rollback_pack/` - delete/remove rollback tools
- `ivr/scripts/` - IVR script read/create/modify/delete tools
- `ivr/builder/` - IVR XML parser, build kit, catalog, compiler, and AI-facing builder facade

Historical root-level import names such as `preflight`, `core_writes`, `modify`, `rollback`, `ivr_scripts`, `ivr_builder`, `soap_client`, and operation modules are preserved as package aliases in `__init__.py`. New work should go into the package folders above.

## API Notes

- Five9 Configuration Web Services uses SOAP.
- Use the v13 admin endpoint: `https://{domain}/wsadmin/v13/AdminWebService`.
- Namespace: `http://service.admin.ws.five9.com/`.
- Auth uses HTTP Basic with `SOAPAction: ""`.
- Avoid `zeep` for the current prompt workflow because swaRef schema handling breaks WSDL parsing.
- Use `pdftotext` to read source PDFs before writing or changing API logic.

## Tool Rules

- One file per API operation using `five9_operation.py` naming, placed in the correct pack folder.
- Dry-run/stub tools must log calls and return planned/mock results.
- Live tools must require explicit human approval before execution.
- Keep Five9 SOAP details out of `src/agent/`.
- Do not alter working Phase 1 prompt upload behavior while building configuration packs unless explicitly requested.
- UI routes should call dispatcher/facade modules, not individual SOAP helpers directly.

## Good Five9 Work

Good work separates request planning from SOAP execution, preserves raw request/response evidence when debugging, and keeps a clear path from a business requirement to an auditable Five9 configuration operation.
