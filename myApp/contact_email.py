"""Send contact form submissions to the admin inbox via Resend."""

from __future__ import annotations

import html
import logging
from typing import Any

import requests
from django.conf import settings

from myApp.forms import INQUIRY_CHOICES

logger = logging.getLogger(__name__)


class ContactEmailError(Exception):
    pass


def _inquiry_label(value: str) -> str:
    labels = dict(INQUIRY_CHOICES)
    return labels.get(value, value)


def send_contact_email(data: dict[str, Any]) -> None:
    api_key = (settings.RESEND_API_KEY or '').strip()
    if not api_key:
        raise ContactEmailError('Contact email is not configured.')

    name = html.escape(data['name'])
    email = html.escape(data['email'])
    inquiry = html.escape(_inquiry_label(data['inquiry_type']))
    organization = html.escape(data.get('organization') or '').strip()
    message = html.escape(data['message']).replace('\n', '<br>')

    org_block = (
        f'<p><strong>Organization:</strong> {organization}</p>'
        if organization
        else ''
    )

    body_html = f"""
    <div style="font-family: 'Segoe UI', system-ui, sans-serif; color: #28332F; line-height: 1.55;">
      <h2 style="color: #1F4E47; margin: 0 0 16px;">New Aira contact form message</h2>
      <p><strong>From:</strong> {name} &lt;{email}&gt;</p>
      <p><strong>Topic:</strong> {inquiry}</p>
      {org_block}
      <hr style="border: none; border-top: 1px solid rgba(31,78,71,0.15); margin: 20px 0;">
      <p style="white-space: pre-wrap;">{message}</p>
      <p style="color: #64756F; font-size: 13px; margin-top: 24px;">
        Reply directly to this email to reach {email}.
      </p>
    </div>
    """

    payload = {
        'from': settings.RESEND_FROM_EMAIL,
        'to': [settings.CONTACT_ADMIN_EMAIL],
        'reply_to': data['email'],
        'subject': f'[Aira] {_inquiry_label(data["inquiry_type"])} — {data["name"]}',
        'html': body_html,
    }

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
        raise ContactEmailError('Could not reach the email service.') from exc

    if response.status_code >= 400:
        logger.error(
            'Resend rejected contact email (%s): %s',
            response.status_code,
            response.text[:500],
        )
        raise ContactEmailError('The email service rejected this message.')
