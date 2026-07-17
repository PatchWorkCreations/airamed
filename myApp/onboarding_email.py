"""Onboarding completion emails (client welcome + internal notification) via Resend."""

from __future__ import annotations

import html
import logging

import requests
from django.conf import settings

from .onboarding import answers_by_step, summary_snapshot

logger = logging.getLogger(__name__)

BRAND_NAVY = '#1B3B7D'
BRAND_TEAL = '#249DA8'
BRAND_INK = '#1A2E4A'
BRAND_MUTED = '#64756F'


class OnboardingEmailError(Exception):
    pass


def _send(payload: dict) -> None:
    api_key = (settings.RESEND_API_KEY or '').strip()
    if not api_key:
        raise OnboardingEmailError('Onboarding email is not configured (RESEND_API_KEY missing).')
    try:
        response = requests.post(
            'https://api.resend.com/emails',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=20,
        )
    except requests.RequestException as exc:
        raise OnboardingEmailError('Could not reach the email service.') from exc

    if response.status_code >= 400:
        logger.error('Resend rejected onboarding email (%s): %s', response.status_code, response.text[:500])
        raise OnboardingEmailError('The email service rejected this message.')


def _wrap(body: str) -> str:
    return f"""
    <div style="font-family: 'Segoe UI', system-ui, sans-serif; color: {BRAND_INK}; line-height: 1.55; max-width: 640px;">
      {body}
      <p style="color: {BRAND_MUTED}; font-size: 13px; margin-top: 28px;">
        AiraMed — The Patient Understanding Platform. Understanding is a clinical outcome.
      </p>
    </div>
    """


def _timeline_html() -> str:
    rows = [
        ('Weeks 1–2', 'Setup & training', 'Clinical staff briefing, consent workflow setup, patient onboarding — no EHR access or IT integration required.'),
        ('Weeks 3–7', 'Active pilot', 'Patients use Record to Remember across selected visits; weekly check-ins with your care team.'),
        ('Weeks 8–9', 'Evaluation', 'Survey review and comparison against your baseline comprehension and satisfaction scores.'),
        ('Week 10', 'Go / no-go decision', 'Joint review of results and the pathway to expanded deployment.'),
    ]
    items = ''.join(
        f'<tr>'
        f'<td style="padding:8px 14px 8px 0; font-weight:700; color:{BRAND_TEAL}; white-space:nowrap; vertical-align:top;">{weeks}</td>'
        f'<td style="padding:8px 0; vertical-align:top;"><strong>{title}</strong><br>'
        f'<span style="color:{BRAND_MUTED}; font-size:14px;">{desc}</span></td>'
        f'</tr>'
        for weeks, title, desc in rows
    )
    return f'<table style="border-collapse:collapse; margin:12px 0;">{items}</table>'


def _recipient_emails(org, submission) -> list[str]:
    seen = []
    for key in ('admin_email', 'champion_email'):
        value = (submission.responses.get(key) or '').strip()
        if value and value.lower() not in {s.lower() for s in seen}:
            seen.append(value)
    if not seen and org.primary_contact_email:
        seen.append(org.primary_contact_email)
    return seen


def send_onboarding_welcome(org, submission) -> None:
    """Branded welcome email confirming scope and what happens next."""
    recipients = _recipient_emails(org, submission)
    if not recipients:
        logger.warning('No recipient email for onboarding welcome (org %s); skipping.', org.pk)
        return

    facts = summary_snapshot(submission.responses)
    org_name = html.escape(facts['org_name'] or org.name)
    dept = html.escape(facts['department'])
    population = html.escape(facts['population'])
    languages = html.escape(facts['languages'])
    start_date = html.escape(facts['start_date'])
    slot = html.escape(facts['slot_1'])

    scope_rows = ''.join(
        f'<tr><td style="padding:6px 16px 6px 0; color:{BRAND_MUTED}; white-space:nowrap;">{label}</td>'
        f'<td style="padding:6px 0; font-weight:600;">{value}</td></tr>'
        for label, value in [
            ('Department', dept or '—'),
            ('Population', population or '—'),
            ('Languages', languages or '—'),
            ('Preferred start', start_date or '—'),
            ('Proposed briefing', slot or '—'),
        ]
    )

    body = f"""
      <h2 style="color:{BRAND_NAVY}; margin:0 0 6px;">Welcome to your AiraMed pilot, {org_name}</h2>
      <p>Your onboarding is complete — thank you. Here's the pilot scope you confirmed:</p>
      <table style="border-collapse:collapse; margin:12px 0 20px;">{scope_rows}</table>
      <h3 style="color:{BRAND_NAVY}; margin:20px 0 6px;">What happens next</h3>
      <p style="margin:0 0 4px;">We'll confirm your staff briefing time within one business day. From there, the 60-day pilot runs:</p>
      {_timeline_html()}
      <p>Questions in the meantime? Just reply to this email.</p>
    """

    _send({
        'from': settings.RESEND_FROM_EMAIL,
        'to': recipients,
        'reply_to': settings.CONTACT_ADMIN_EMAIL,
        'subject': f'Welcome to your AiraMed pilot — next steps for {facts["org_name"] or org.name}',
        'html': _wrap(body),
    })


def send_onboarding_internal(org, submission, invite_url: str) -> None:
    """Full answer dump to the AiraMed team when a client completes onboarding."""
    facts = summary_snapshot(submission.responses)
    sections = []
    for group in answers_by_step(submission.responses):
        rows = ''.join(
            f'<tr><td style="padding:5px 16px 5px 0; color:{BRAND_MUTED}; vertical-align:top; width:45%;">{html.escape(row["label"])}</td>'
            f'<td style="padding:5px 0; vertical-align:top;">{html.escape(row["value"])}</td></tr>'
            for row in group['rows']
        )
        sections.append(
            f'<h3 style="color:{BRAND_NAVY}; margin:22px 0 6px;">Step {group["number"]} — {html.escape(group["title"])}</h3>'
            f'<table style="border-collapse:collapse; width:100%; font-size:14px;">{rows}</table>'
        )

    body = f"""
      <h2 style="color:{BRAND_NAVY}; margin:0 0 6px;">Onboarding complete: {html.escape(facts['org_name'] or org.name)}</h2>
      <p style="margin:0 0 4px;">
        <strong>{html.escape(facts['department'] or '—')}</strong> · {html.escape(facts['population'] or '—')}
        · preferred start {html.escape(facts['start_date'] or '—')}
      </p>
      <p style="margin:0 0 12px;">Proposed briefing: <strong>{html.escape(facts['slot_1'] or '—')}</strong></p>
      <p style="margin:0 0 12px;"><a href="{html.escape(invite_url)}" style="color:{BRAND_TEAL};">Client onboarding link</a></p>
      {''.join(sections)}
    """

    _send({
        'from': settings.RESEND_FROM_EMAIL,
        'to': [settings.CONTACT_ADMIN_EMAIL],
        'subject': f'[AiraMed] Onboarding complete — {facts["org_name"] or org.name}',
        'html': _wrap(body),
    })
