"""Public client onboarding wizard — evergreen /onboard/ plus tokenized resume links."""

from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import ClientOrganization, OnboardingSubmission
from .onboarding import STEPS, TOTAL_STEPS, answers_by_step, extract_answers, get_step
from .onboarding_email import send_onboarding_internal, send_onboarding_welcome

logger = logging.getLogger(__name__)


def _invite_url(request, org: ClientOrganization) -> str:
    return request.build_absolute_uri(reverse('onboarding_resume', args=[org.invite_token]))


def _wizard_context(request, step: dict, *, org=None, values=None, errors=None) -> dict:
    return {
        'step': step,
        'total_steps': TOTAL_STEPS,
        'steps_nav': [{'number': s['number'], 'nav_label': s['nav_label']} for s in STEPS],
        'org': org,
        'values': values or {},
        'errors': errors or {},
        'invite_url': _invite_url(request, org) if org else '',
    }


def _prefill_from_org(org: ClientOrganization, responses: dict) -> dict:
    """Seed step-1 answers for invited clients so they don't retype what we know."""
    values = dict(responses)
    values.setdefault('org_name', org.name)
    values.setdefault('department', org.department)
    values.setdefault('admin_name', org.primary_contact_name)
    values.setdefault('admin_email', org.primary_contact_email)
    return values


@require_http_methods(['GET', 'POST'])
def onboarding_start(request):
    """Evergreen link: step 1 for a brand-new client. Creates their org + token on submit."""
    step = get_step(1)

    if request.method == 'POST':
        data, errors = extract_answers(step, request.POST)
        if errors:
            return render(request, 'myApp/onboarding/step.html',
                          _wizard_context(request, step, values=data, errors=errors))

        org = ClientOrganization.objects.create(
            name=data.get('org_name') or 'Unnamed organization',
            department=data.get('department') or '',
            primary_contact_name=data.get('admin_name') or '',
            primary_contact_email=data.get('admin_email') or '',
            source=ClientOrganization.SOURCE_SELF_SERVE,
            status=ClientOrganization.STATUS_INTAKE_STARTED,
        )
        OnboardingSubmission.objects.create(organization=org, responses=data, current_step=2)
        return redirect('onboarding_step', token=org.invite_token, step=2)

    return render(request, 'myApp/onboarding/step.html', _wizard_context(request, step))


def _get_org_and_submission(token) -> tuple[ClientOrganization, OnboardingSubmission]:
    org = get_object_or_404(ClientOrganization, invite_token=token)
    submission, _ = OnboardingSubmission.objects.get_or_create(organization=org)
    return org, submission


@require_http_methods(['GET'])
def onboarding_resume(request, token):
    """The link clients bookmark / receive: drops them at their next step."""
    org, submission = _get_org_and_submission(token)
    if submission.is_complete:
        return redirect('onboarding_done', token=org.invite_token)
    if org.status == ClientOrganization.STATUS_INVITED:
        org.status = ClientOrganization.STATUS_INTAKE_STARTED
        org.save(update_fields=['status', 'updated_at'])
    return redirect('onboarding_step', token=org.invite_token, step=min(submission.current_step, TOTAL_STEPS))


@require_http_methods(['GET', 'POST'])
def onboarding_step(request, token, step: int):
    org, submission = _get_org_and_submission(token)
    if submission.is_complete:
        return redirect('onboarding_done', token=org.invite_token)

    step_def = get_step(step)
    if step_def is None:
        return redirect('onboarding_resume', token=org.invite_token)
    # No skipping ahead of the furthest unlocked step.
    if step > submission.current_step:
        return redirect('onboarding_step', token=org.invite_token, step=submission.current_step)

    if request.method == 'POST':
        data, errors = extract_answers(step_def, request.POST)
        if errors:
            return render(request, 'myApp/onboarding/step.html',
                          _wizard_context(request, step_def, org=org, values=data, errors=errors))

        submission.responses = {**submission.responses, **data}
        is_final = step >= TOTAL_STEPS
        if not is_final:
            submission.current_step = max(submission.current_step, step + 1)
            submission.save(update_fields=['responses', 'current_step', 'updated_at'])
            return redirect('onboarding_step', token=org.invite_token, step=step + 1)

        submission.completed_at = timezone.now()
        submission.current_step = TOTAL_STEPS
        submission.save(update_fields=['responses', 'current_step', 'completed_at', 'updated_at'])

        # Keep the org record in sync with the final answers.
        org.name = submission.responses.get('org_name') or org.name
        org.department = submission.responses.get('department') or org.department
        org.primary_contact_name = submission.responses.get('admin_name') or org.primary_contact_name
        org.primary_contact_email = submission.responses.get('admin_email') or org.primary_contact_email
        org.status = ClientOrganization.STATUS_INTAKE_COMPLETE
        org.save()

        # Email failures must never block the client's confirmation screen.
        try:
            send_onboarding_welcome(org, submission)
        except Exception:
            logger.exception('Onboarding welcome email failed for org %s', org.pk)
        try:
            send_onboarding_internal(org, submission, _invite_url(request, org))
        except Exception:
            logger.exception('Onboarding internal notification failed for org %s', org.pk)

        return redirect('onboarding_done', token=org.invite_token)

    values = submission.responses
    if step == 1:
        values = _prefill_from_org(org, values)
    return render(request, 'myApp/onboarding/step.html',
                  _wizard_context(request, step_def, org=org, values=values))


@require_http_methods(['GET'])
def onboarding_done(request, token):
    org, submission = _get_org_and_submission(token)
    if not submission.is_complete:
        return redirect('onboarding_resume', token=org.invite_token)
    return render(request, 'myApp/onboarding/done.html', {
        'org': org,
        'submission': submission,
        'answer_groups': answers_by_step(submission.responses),
        'timeline': [
            {'weeks': 'Weeks 1–2', 'title': 'Setup & training', 'desc': 'Clinical staff briefing, consent workflow setup, and patient onboarding — no EHR access or IT integration required.'},
            {'weeks': 'Weeks 3–7', 'title': 'Active pilot', 'desc': 'Patients use Record to Remember across selected visits; weekly check-ins with your care team.'},
            {'weeks': 'Weeks 8–9', 'title': 'Evaluation', 'desc': 'Survey review and comparison against your baseline comprehension and satisfaction scores.'},
            {'weeks': 'Week 10', 'title': 'Go / no-go decision', 'desc': 'Joint review of results and the pathway to expanded or system-wide deployment.'},
        ],
    })
