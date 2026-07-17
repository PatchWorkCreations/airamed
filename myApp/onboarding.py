"""Step definitions and helpers for the client onboarding wizard.

The wizard is data-driven: STEPS below describes every field, and both the
public wizard templates and the pilot dashboard render from it. Adding a
question means adding one dict here — no template changes required.
"""

from __future__ import annotations

from typing import Any

STEPS = [
    {
        'number': 1,
        'key': 'org',
        'title': 'Your organization',
        'nav_label': 'Organization',
        'intro': 'Tell us who we are partnering with and who leads the pilot on your side.',
        'sections': [
            {
                'heading': 'Organization',
                'fields': [
                    {'key': 'org_name', 'label': 'Health system / hospital name', 'type': 'text', 'required': True, 'placeholder': 'e.g. Mercy General Health System'},
                    {'key': 'department', 'label': 'Pilot department or service line', 'type': 'select', 'required': True, 'options': ['Cardiology', 'Geriatrics', 'Primary care', 'Oncology', 'Discharge / transitional care', 'Other']},
                    {'key': 'department_other', 'label': 'If other, which department?', 'type': 'text', 'required': False, 'placeholder': 'Department name'},
                ],
            },
            {
                'heading': 'Clinical champion',
                'help': 'The physician or nurse leader sponsoring the pilot clinically.',
                'fields': [
                    {'key': 'champion_name', 'label': 'Full name', 'type': 'text', 'required': True},
                    {'key': 'champion_role', 'label': 'Role / title', 'type': 'text', 'required': True, 'placeholder': 'e.g. Chief of Cardiology'},
                    {'key': 'champion_email', 'label': 'Email', 'type': 'email', 'required': True},
                    {'key': 'champion_phone', 'label': 'Phone', 'type': 'tel', 'required': False},
                ],
            },
            {
                'heading': 'Administrative contact',
                'help': 'Our day-to-day coordination contact for scheduling and logistics.',
                'fields': [
                    {'key': 'admin_name', 'label': 'Full name', 'type': 'text', 'required': True},
                    {'key': 'admin_email', 'label': 'Email', 'type': 'email', 'required': True},
                ],
            },
            {
                'heading': 'IT / security contact',
                'help': 'Optional for Phase 1 — no EHR integration is required to launch.',
                'fields': [
                    {'key': 'it_name', 'label': 'Full name', 'type': 'text', 'required': False},
                    {'key': 'it_email', 'label': 'Email', 'type': 'email', 'required': False},
                ],
            },
        ],
    },
    {
        'number': 2,
        'key': 'scope',
        'title': 'Pilot scope',
        'nav_label': 'Pilot scope',
        'intro': 'Define the population and visits the 60-day pilot will cover.',
        'sections': [
            {
                'heading': 'Patient population',
                'fields': [
                    {'key': 'population', 'label': 'Which patients will the pilot include?', 'type': 'multiselect', 'required': True, 'options': ['Patients 65+', 'Limited-English patients', 'Complex discharge patients', 'All patients in the department']},
                    {'key': 'languages', 'label': 'Languages needed beyond English', 'type': 'text', 'required': False, 'placeholder': 'e.g. Spanish, Mandarin, Tagalog'},
                    {'key': 'patient_count', 'label': 'Estimated patients during the pilot', 'type': 'select', 'required': True, 'options': ['Fewer than 25', '25–50', '51–100', 'More than 100', 'Not sure yet']},
                ],
            },
            {
                'heading': 'Visits & timing',
                'fields': [
                    {'key': 'visit_types', 'label': 'Which visit types should Record to Remember cover?', 'type': 'multiselect', 'required': True, 'options': ['Inpatient discharge', 'Outpatient clinic visits', 'Post-op follow-ups', 'Telehealth visits']},
                    {'key': 'start_date', 'label': 'Preferred pilot start date', 'type': 'date', 'required': True},
                ],
            },
        ],
    },
    {
        'number': 3,
        'key': 'governance',
        'title': 'Governance & consent',
        'nav_label': 'Governance',
        'intro': 'Privacy and clinical governance are designed in from day one. A few questions so we arrive prepared.',
        'sections': [
            {
                'heading': 'Agreements',
                'fields': [
                    {'key': 'baa_required', 'label': 'Will your organization require a Business Associate Agreement (BAA) before launch?', 'type': 'radio', 'required': True, 'options': ['Yes', 'No', 'Not sure — need to check']},
                    {'key': 'privacy_review', 'label': 'Does this pilot need review by your privacy / compliance office?', 'type': 'radio', 'required': True, 'options': ['Yes', 'No', 'Not sure — need to check']},
                ],
            },
            {
                'heading': 'Patient consent',
                'fields': [
                    {'key': 'consent_preference', 'label': 'How would you like to handle patient recording consent?', 'type': 'radio', 'required': True, 'options': ['Use the AiraMed standard consent script', 'Use our own consent form', 'Need guidance from AiraMed']},
                    {'key': 'governance_notes', 'label': 'Anything your security or compliance team will want us to know?', 'type': 'textarea', 'required': False, 'placeholder': 'Security questionnaires, review board timelines, data residency requirements…'},
                ],
            },
        ],
    },
    {
        'number': 4,
        'key': 'baseline',
        'title': 'Baseline metrics',
        'nav_label': 'Baselines',
        'intro': 'These numbers are how we prove pilot outcomes at week 8–9. Estimates are fine — and we can help you pull them.',
        'sections': [
            {
                'heading': 'Current-state numbers',
                'fields': [
                    {'key': 'callbacks_weekly', 'label': 'Average nurse callbacks per week (pilot department)', 'type': 'text', 'required': False, 'placeholder': 'e.g. 40'},
                    {'key': 'cahps_score', 'label': 'Most recent CAHPS communication score', 'type': 'text', 'required': False, 'placeholder': 'e.g. 78'},
                    {'key': 'readmission_rate', 'label': '30-day readmission rate for the pilot population', 'type': 'text', 'required': False, 'placeholder': 'e.g. 14%'},
                    {'key': 'noshow_rate', 'label': 'Follow-up appointment no-show rate', 'type': 'text', 'required': False, 'placeholder': 'e.g. 20%'},
                ],
            },
            {
                'heading': 'Data availability',
                'fields': [
                    {'key': 'metrics_help', 'label': 'How should we handle baseline data?', 'type': 'radio', 'required': True, 'options': ['We have these numbers and filled them in', 'We need help pulling them', 'Let’s discuss at kickoff']},
                ],
            },
        ],
    },
    {
        'number': 5,
        'key': 'kickoff',
        'title': 'Kickoff & training',
        'nav_label': 'Kickoff',
        'intro': 'Weeks 1–2 of the pilot are setup and training. Let’s get the staff briefing on the calendar.',
        'sections': [
            {
                'heading': 'Staff briefing — proposed times',
                'help': 'Give us two or three windows that work for your team; we will confirm one within a business day.',
                'fields': [
                    {'key': 'slot_1', 'label': 'First choice', 'type': 'text', 'required': True, 'placeholder': 'e.g. Tue Aug 4, 10:00–11:00 AM ET'},
                    {'key': 'slot_2', 'label': 'Second choice', 'type': 'text', 'required': False, 'placeholder': 'e.g. Wed Aug 5, 2:00–3:00 PM ET'},
                    {'key': 'slot_3', 'label': 'Third choice', 'type': 'text', 'required': False},
                ],
            },
            {
                'heading': 'Attendees & final details',
                'fields': [
                    {'key': 'training_attendees', 'label': 'Who will attend the staff briefing? (names / roles)', 'type': 'textarea', 'required': True, 'placeholder': 'e.g. Dr. Alvarez (champion), 2 charge nurses, discharge coordinator…'},
                    {'key': 'timeline_ack', 'label': 'We understand the 60-day pilot timeline: setup & training (weeks 1–2), active pilot (weeks 3–7), evaluation (weeks 8–9), go/no-go review (week 10).', 'type': 'checkbox', 'required': True},
                    {'key': 'anything_else', 'label': 'Anything else we should know before kickoff?', 'type': 'textarea', 'required': False},
                ],
            },
        ],
    },
]

TOTAL_STEPS = len(STEPS)

FIELD_TYPES_MULTI = {'multiselect'}
FIELD_TYPES_BOOL = {'checkbox'}


def get_step(number: int) -> dict | None:
    for step in STEPS:
        if step['number'] == number:
            return step
    return None


def step_fields(step: dict) -> list[dict]:
    return [field for section in step['sections'] for field in section['fields']]


def extract_answers(step: dict, post) -> tuple[dict[str, Any], dict[str, str]]:
    """Pull this step's answers out of request.POST and validate required fields."""
    data: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for field in step_fields(step):
        key = field['key']
        if field['type'] in FIELD_TYPES_MULTI:
            value: Any = [v.strip() for v in post.getlist(key) if v.strip()]
            if field.get('options'):
                value = [v for v in value if v in field['options']]
        elif field['type'] in FIELD_TYPES_BOOL:
            value = post.get(key) == 'on'
        else:
            value = (post.get(key) or '').strip()
            if field.get('options') and value and value not in field['options']:
                value = ''
        data[key] = value
        if field.get('required') and not value:
            errors[key] = 'This field is required.'
    return data, errors


def _display_value(field: dict, value: Any) -> str:
    if value in (None, '', []):
        return '—'
    if field['type'] in FIELD_TYPES_MULTI and isinstance(value, list):
        return ', '.join(str(v) for v in value)
    if field['type'] in FIELD_TYPES_BOOL:
        return 'Yes' if value else 'No'
    return str(value)


def answers_by_step(responses: dict) -> list[dict]:
    """Group saved answers for display (dashboard detail, internal email)."""
    grouped = []
    for step in STEPS:
        rows = [
            {'label': field['label'], 'value': _display_value(field, responses.get(field['key']))}
            for field in step_fields(step)
        ]
        grouped.append({'number': step['number'], 'title': step['title'], 'rows': rows})
    return grouped


def summary_snapshot(responses: dict) -> dict[str, str]:
    """Key facts used in emails and the dashboard list."""
    population = responses.get('population') or []
    return {
        'org_name': responses.get('org_name') or '',
        'department': responses.get('department') or '',
        'population': ', '.join(population) if isinstance(population, list) else str(population),
        'languages': responses.get('languages') or 'English only',
        'start_date': responses.get('start_date') or '',
        'patient_count': responses.get('patient_count') or '',
        'slot_1': responses.get('slot_1') or '',
    }
