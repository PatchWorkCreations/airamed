import json
from datetime import datetime
from functools import wraps

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import voice_ai
from .contact_email import ContactEmailError, send_contact_email
from .forms import ContactForm
from .models import PilotSurveyResponse, PlannerLead
from .summary_email import SummaryEmailError, send_summary_email

PILOT_SURVEY_ROLES = {PilotSurveyResponse.ROLE_PATIENT, PilotSurveyResponse.ROLE_CAREGIVER, PilotSurveyResponse.ROLE_NURSE}


def home(request):
    return render(request, 'myApp/home.html', {'active': 'home'})


def about(request):
    return render(request, 'myApp/about.html', {'active': 'about'})


def our_story(request):
    return render(request, 'myApp/our_story.html', {'active': 'our_story'})


def faq(request):
    return render(request, 'myApp/faq.html', {'active': 'faq'})


def privacy(request):
    return render(request, 'myApp/privacy.html', {'active': 'privacy'})


def terms(request):
    return render(request, 'myApp/terms.html', {'active': 'terms'})


def contact(request):
    sent = False
    form = ContactForm()

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            try:
                send_contact_email(form.cleaned_data)
            except ContactEmailError:
                messages.error(
                    request,
                    'We couldn\'t send your message right now. Please try again in a few minutes.',
                )
            else:
                sent = True
                form = ContactForm()

    return render(request, 'myApp/contact.html', {
        'active': 'contact',
        'form': form,
        'sent': sent,
    })


# --- "Record & remember" API ------------------------------------------------
# These JSON endpoints use plain Django (no DRF). They are csrf_exempt because
# the recorder posts many small chunks; revisit this before any real deployment.

@csrf_exempt
@require_POST
def voice_transcribe(request):
    """Transcribe a single base64 audio chunk via Whisper.

    Body: {"audio": "<base64>", "format": "webm|wav|mp3|m4a|ogg"}
    Always returns HTTP 200 with {"text": "..."} (possibly empty + a "note"),
    so silence between speech never surfaces as an error in the recorder UI.
    """
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({'error': 'invalid_json'}, status=400)

    audio_b64 = data.get('audio')
    if not audio_b64:
        return JsonResponse({'text': '', 'note': 'no_audio'})

    result = voice_ai.transcribe_audio_b64(
        audio_b64,
        data.get('format', 'webm'),
        language=data.get('language'),
    )
    return JsonResponse(result)


@csrf_exempt
@require_POST
def visit_summarize(request):
    """Turn a full visit transcript into a summary and doctor questions via GPT.

    Body: {"transcript": "..."} -> {"summary": "...", "doctor_questions": [...]}
    """
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({'error': 'invalid_json'}, status=400)

    transcript = (data.get('transcript') or '').strip()
    if not transcript:
        return JsonResponse({'summary': '', 'doctor_questions': []})

    try:
        result = voice_ai.summarize_visit(transcript)
    except Exception:
        return JsonResponse({'error': 'summary_failed'}, status=502)

    return JsonResponse(result)


MAX_SUMMARY_CHARS = 20000
MAX_QUESTIONS = 20
MAX_QUESTION_CHARS = 500


@csrf_exempt
@require_POST
def visit_email_summary(request):
    """Email a visit summary and doctor questions to the user via Resend.

    Body: {"email": "...", "summary": "...", "doctor_questions": ["...", ...]}
    """
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({'error': 'invalid_json'}, status=400)

    email = (data.get('email') or '').strip()
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'error': 'invalid_email'}, status=400)

    summary = (data.get('summary') or '').strip()
    if not summary:
        return JsonResponse({'error': 'missing_summary'}, status=400)
    summary = summary[:MAX_SUMMARY_CHARS]

    raw_questions = data.get('doctor_questions') or []
    if not isinstance(raw_questions, list):
        raw_questions = []
    questions = [
        str(q).strip()[:MAX_QUESTION_CHARS]
        for q in raw_questions[:MAX_QUESTIONS]
        if str(q).strip()
    ]

    try:
        send_summary_email(to_email=email, summary_md=summary, doctor_questions=questions)
    except SummaryEmailError:
        return JsonResponse({'error': 'email_failed'}, status=502)

    return JsonResponse({'ok': True})


@csrf_exempt
@require_POST
def pilot_survey_submit(request):
    """Store a 60-day pilot dashboard survey response.

    Body: {"role": "patient|caregiver|nurse", "responses": {...}}
    """
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({'error': 'invalid_json'}, status=400)

    role = (data.get('role') or '').strip()
    if role not in PILOT_SURVEY_ROLES:
        return JsonResponse({'error': 'invalid_role'}, status=400)

    responses = data.get('responses')
    if not isinstance(responses, dict) or not responses:
        return JsonResponse({'error': 'missing_responses'}, status=400)

    PilotSurveyResponse.objects.create(role=role, responses=responses)
    return JsonResponse({'ok': True})


def _cors_json(view_func):
    """Attach browser CORS headers for cross-origin landing-page POSTs."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method == 'OPTIONS':
            response = HttpResponse(status=204)
        else:
            response = view_func(request, *args, **kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    return wrapper


def _parse_submitted_at(value):
    if not value or not isinstance(value, str):
        return None
    parsed = parse_datetime(value.strip())
    if parsed is not None:
        return parsed
    try:
        return datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None


@csrf_exempt
@_cors_json
def planner_signup_webhook(request):
    """Public webhook for Patch Wetzel planner email signups.

    Body: {
      "email": "...",
      "source": "Patch Wetzel landing page",
      "lead": "Power of the Breath 2027 Planner",
      "submitted_at": "2026-07-13T16:00:00.000Z"
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'method_not_allowed'}, status=405)

    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({'error': 'invalid_json'}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({'error': 'invalid_json'}, status=400)

    email = (data.get('email') or '').strip()
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'error': 'invalid_email'}, status=400)

    source = str(data.get('source') or '').strip()[:255]
    lead = str(data.get('lead') or '').strip()[:255]
    submitted_at = _parse_submitted_at(data.get('submitted_at'))

    PlannerLead.objects.create(
        email=email,
        source=source,
        lead=lead,
        tag=PlannerLead.DEFAULT_TAG,
        submitted_at=submitted_at,
    )
    return JsonResponse({'ok': True})
