import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import voice_ai
from .contact_email import ContactEmailError, send_contact_email
from .forms import ContactForm


def home(request):
    return render(request, 'myApp/home.html', {'active': 'home'})


def about(request):
    return render(request, 'myApp/about.html', {'active': 'about'})


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
    """Turn a full visit transcript into a structured Visit Summary via GPT.

    Body: {"transcript": "..."} -> {"summary": "..."} or 502 on failure.
    """
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({'error': 'invalid_json'}, status=400)

    transcript = (data.get('transcript') or '').strip()
    if not transcript:
        return JsonResponse({'summary': ''})

    try:
        result = voice_ai.summarize_visit(transcript)
    except Exception:
        return JsonResponse({'error': 'summary_failed'}, status=502)

    return JsonResponse(result)
