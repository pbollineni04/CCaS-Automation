# Five9 Tools Workspace

Last updated: 2026-05-06

Five9 is the primary CCaaS platform for Phase 1 and the Phase 2 demo. This workspace contains the working prompt bulk upload tool, Five9 SOAP API PDFs, and future Five9-specific operation tools.

## Existing Phase 1

Working code:

- `Prompt_Management/Prompt_Bulk_Upload/five9_prompts.py` - raw SOAP prompt operations
- `Prompt_Management/Prompt_Bulk_Upload/bulk_upload.py` - CLI bulk upload entry point
- `Prompt_Management/Prompt_Bulk_Upload/sample_manifest.csv` - sample upload manifest

## API Notes

- Five9 Configuration Web Services uses SOAP.
- Use the v13 admin endpoint: `https://{domain}/wsadmin/v13/AdminWebService`.
- Namespace: `http://service.admin.ws.five9.com/`.
- Auth uses HTTP Basic with `SOAPAction: ""`.
- Avoid `zeep` for the current prompt workflow because swaRef schema handling breaks WSDL parsing.
- Use `pdftotext` to read source PDFs before writing or changing API logic.

## Tool Rules

- One file per API operation using `five9_operation.py` naming.
- Stub tools must log calls and return mock results.
- Live tools must require explicit human approval before execution.
- Keep Five9 SOAP details out of `src/agent/`.
- Do not alter working Phase 1 prompt upload behavior while building Phase 2 stubs unless explicitly requested.

## Good Five9 Work

Good work separates request planning from SOAP execution, preserves raw request/response evidence when debugging, and keeps a clear path from a business requirement to an auditable Five9 configuration operation.
