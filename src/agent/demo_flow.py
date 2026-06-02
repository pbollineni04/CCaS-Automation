from copy import deepcopy
from datetime import datetime


DEFAULT_DISCOVERY_TEMPLATE = """Client: Acme Health Services

Business Hours:
Monday-Friday, 8:00 AM-6:00 PM Eastern.
After-hours callers should hear a closed message and route to voicemail.

Queues:
- Sales
- Billing
- Support

Skills:
- English
- Spanish
- Billing Specialist
- Sales Specialist

Dispositions:
- Sale Completed
- Billing Resolved
- Follow Up Required
- Transferred to Support

Prompts:
- Main greeting: "Thank you for calling Acme Health Services. Please listen carefully as our menu options have changed."
- After-hours: "You have reached us outside normal business hours. Please leave a message and we will return your call."

DNIS / Routing:
- 800-555-0100 routes to Main IVR.
- Main IVR option 1 routes to Sales queue.
- Main IVR option 2 routes to Billing queue.
- Main IVR option 3 routes to Support queue.

IVR Intent:
Create a simple main IVR that routes callers by menu selection and respects business hours.
"""

REQUIREMENT_GROUPS = {
    "Business Hours": [
        "Set business hours to Monday-Friday, 8:00 AM-6:00 PM Eastern",
        "After-hours callers hear the closed message and route to voicemail",
    ],
    "Queues": [
        "Create Sales queue",
        "Create Billing queue",
        "Create Support queue",
    ],
    "Skills": [
        "Add English skill",
        "Add Spanish skill",
        "Add Billing Specialist skill",
        "Add Sales Specialist skill",
    ],
    "Dispositions": [
        "Create Sale Completed disposition",
        "Create Billing Resolved disposition",
        "Create Follow Up Required disposition",
        "Create Transferred to Support disposition",
    ],
    "Prompts": [
        "Create main greeting prompt",
        "Create after-hours prompt",
    ],
    "DNIS / Routing": [
        "Route DNIS 800-555-0100 to Main IVR",
        "Route Main IVR option 1 to Sales queue",
        "Route Main IVR option 2 to Billing queue",
        "Route Main IVR option 3 to Support queue",
    ],
    "IVR Intent": [
        "Configure Main IVR options for Sales, Billing, and Support",
        "Configure Main IVR to respect business hours",
    ],
}

PLANNED_CALLS = [
    {
        "tool_name": "five9_create_skill",
        "params": {
            "name": "English",
            "description": "Language skill for English-speaking callers",
        },
    },
    {
        "tool_name": "five9_create_skill",
        "params": {
            "name": "Spanish",
            "description": "Language skill for Spanish-speaking callers",
        },
    },
    {
        "tool_name": "five9_create_skill",
        "params": {
            "name": "Billing Specialist",
            "description": "Skill for billing support calls",
        },
    },
    {
        "tool_name": "five9_create_skill",
        "params": {
            "name": "Sales Specialist",
            "description": "Skill for sales calls",
        },
    },
    {
        "tool_name": "five9_create_disposition",
        "params": {"name": "Sale Completed"},
    },
    {
        "tool_name": "five9_create_disposition",
        "params": {"name": "Billing Resolved"},
    },
    {
        "tool_name": "five9_create_disposition",
        "params": {"name": "Follow Up Required"},
    },
    {
        "tool_name": "five9_create_disposition",
        "params": {"name": "Transferred to Support"},
    },
    {
        "tool_name": "five9_add_prompt_tts",
        "params": {
            "prompt_name": "Main Greeting",
            "text": "Thank you for calling Acme Health Services. Please listen carefully as our menu options have changed.",
        },
    },
    {
        "tool_name": "five9_add_prompt_tts",
        "params": {
            "prompt_name": "After Hours",
            "text": "You have reached us outside normal business hours. Please leave a message and we will return your call.",
        },
    },
    {
        "tool_name": "five9_create_inbound_campaign",
        "params": {
            "campaign_name": "Acme Main Inbound",
            "default_ivr_script_name": "Main IVR",
            "queues": ["Sales", "Billing", "Support"],
        },
    },
    {
        "tool_name": "five9_add_dnis_to_campaign",
        "params": {
            "dnis": "800-555-0100",
            "campaign_name": "Acme Main Inbound",
            "route_to": "Main IVR",
        },
    },
    {
        "tool_name": "five9_add_skills_to_campaign",
        "params": {
            "campaign_name": "Acme Main Inbound",
            "skills": [
                "English",
                "Spanish",
                "Billing Specialist",
                "Sales Specialist",
            ],
        },
    },
    {
        "tool_name": "five9_set_default_ivr_schedule",
        "params": {
            "ivr_name": "Main IVR",
            "timezone": "Eastern",
            "open_hours": "Monday-Friday 8:00 AM-6:00 PM",
            "after_hours_prompt": "After Hours",
        },
    },
]

ALLOWED_DEMO_TOOL_NAMES = {call["tool_name"] for call in PLANNED_CALLS}
STUB_EXECUTION_MESSAGE = "Stub execution complete. No live Five9 changes were made."


def analyze_requirements(input_text):
    if not input_text or not input_text.strip():
        raise ValueError("Discovery template input is required.")

    return {
        "requirements": deepcopy(REQUIREMENT_GROUPS),
        "planned_calls": deepcopy(PLANNED_CALLS),
    }


def execute_stub_plan(approved, planned_calls):
    if approved is not True:
        raise PermissionError("Human approval is required before stub execution.")

    _validate_planned_calls(planned_calls)

    logs = []
    for call in planned_calls:
        logs.append(
            {
                "tool_name": call["tool_name"],
                "params": deepcopy(call["params"]),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "mode": "stub",
                "result": "success",
            }
        )
    return logs


def _validate_planned_calls(planned_calls):
    if planned_calls != PLANNED_CALLS:
        _raise_plan_validation_error(planned_calls)


def _raise_plan_validation_error(planned_calls):
    unknown_tools = [
        call.get("tool_name")
        for call in planned_calls or []
        if call.get("tool_name") not in ALLOWED_DEMO_TOOL_NAMES
    ]
    if unknown_tools:
        raise ValueError(f"Unknown demo tool name: {unknown_tools[0]}")
    raise ValueError("Only the deterministic demo planned-call list can be executed.")
