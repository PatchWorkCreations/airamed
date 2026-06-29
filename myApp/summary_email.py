"""Email a visit summary and doctor questions to the user via Resend."""

from __future__ import annotations

import html
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class SummaryEmailError(Exception):
    pass


def _md_inline(text: str) -> str:
    """Escape, then apply a tiny subset of inline markdown (**bold**, *italic*)."""
    escaped = html.escape(text)
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)
    escaped = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', escaped)
    return escaped


def _markdown_to_html(md: str) -> str:
    """Mirror the client renderMarkdown(): headings, bullet lists, paragraphs."""
    lines = str(md).splitlines()
    out: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append('</ul>')
            in_list = False

    for raw in lines:
        line = raw.strip()
        if not line:
            close_list()
            continue
        heading = re.match(r'^#{1,6}\s+(.*)$', line)
        if heading:
            close_list()
            out.append(
                '<h3 style="color:#1F4E47;margin:20px 0 8px;font-size:16px;">'
                + _md_inline(heading.group(1))
                + '</h3>'
            )
            continue
        bullet = re.match(r'^[-*]\s+(.*)$', line)
        if bullet:
            if not in_list:
                out.append('<ul style="margin:0 0 12px;padding-left:20px;">')
                in_list = True
            out.append('<li style="margin:4px 0;">' + _md_inline(bullet.group(1)) + '</li>')
            continue
        close_list()
        out.append('<p style="margin:0 0 12px;">' + _md_inline(line) + '</p>')

    close_list()
    return ''.join(out)


def send_summary_email(*, to_email: str, summary_md: str, doctor_questions: list[str]) -> None:
    api_key = (settings.RESEND_API_KEY or '').strip()
    if not api_key:
        raise SummaryEmailError('Summary email is not configured.')

    summary_html = _markdown_to_html(summary_md)

    questions_block = ''
    if doctor_questions:
        items = ''.join(
            '<li style="margin:6px 0;">' + html.escape(str(q)) + '</li>'
            for q in doctor_questions
            if str(q).strip()
        )
        if items:
            questions_block = f"""
      <h2 style="color: #1F4E47; margin: 28px 0 8px; font-size: 18px;">Questions for your doctor</h2>
      <ol style="margin: 0 0 12px; padding-left: 20px; color: #28332F;">{items}</ol>
      """

    body_html = f"""
    <div style="font-family: 'Segoe UI', system-ui, sans-serif; color: #28332F; line-height: 1.55; max-width: 640px;">
      <h1 style="color: #1F4E47; margin: 0 0 16px; font-size: 22px;">Your Aira visit summary</h1>
      <div style="color: #28332F;">{summary_html}</div>
      {questions_block}
      <hr style="border: none; border-top: 1px solid rgba(31,78,71,0.15); margin: 24px 0;">
      <p style="color: #64756F; font-size: 13px; margin: 0;">
        This summary is a memory aid, not medical advice. Always follow your care team's
        instructions, and seek urgent care if something feels wrong. This inbox is not monitored.
      </p>
    </div>
    """

    payload = {
        'from': settings.RESEND_FROM_EMAIL,
        'to': [to_email],
        'subject': 'Your Aira visit summary',
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
        raise SummaryEmailError('Could not reach the email service.') from exc

    if response.status_code >= 400:
        logger.error(
            'Resend rejected summary email (%s): %s',
            response.status_code,
            response.text[:500],
        )
        raise SummaryEmailError('The email service rejected this message.')
