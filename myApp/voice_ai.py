"""OpenAI-backed helpers for the "Record & remember" doctor-visit recorder.

This is the only module that imports the OpenAI SDK. It exposes:

- ``transcribe_audio_b64`` — turn one short base64 audio chunk into text (Whisper).
- ``summarize_visit``      — turn a full transcript into a structured Visit Summary (GPT).

The OpenAI client is created lazily so importing this module (and therefore the
views) never fails just because ``OPENAI_API_KEY`` is unset — the key is only
required when an endpoint is actually called.
"""

import base64
import logging
import os
import tempfile

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

# Audio container formats the client may send. Whisper infers the codec from the
# temp-file *suffix*, so the suffix must match the real container.
ALLOWED_FORMATS = {"webm", "wav", "mp3", "m4a", "ogg"}

# Chunks smaller than this are almost certainly silence/noise — skip the API call.
MIN_BLOB_BYTES = 1400

# Whisper tends to "hallucinate" these on near-silent audio. Treat them as empty.
# Only EXACT matches are dropped — we no longer filter by length, because many
# languages (e.g. Chinese/Japanese/Korean) carry full meaning in 1-2 characters.
FILTERED_PHRASES = {
    "uh", "um", "okay", "ok", "mm", "hmm", "mhm", "you",
    "thank you", "thanks for watching", ".", "..", "...",
}

# Light context hint for Whisper. Deliberately NEUTRAL: we do NOT include phone
# number / URL examples here, because priming Whisper with them makes it
# hallucinate phone numbers and "visit www..." lines on quiet audio. We only send
# it for English / auto-detect to avoid skewing other languages.
TRANSCRIBE_PROMPT = (
    "This is a conversation during a medical appointment between a patient and a "
    "clinician. Write numbers, dates, and dosages using digits."
)

# Whisper fabricates these stock phrases on silence/noise (YouTube outros, PSAs,
# subtitle credits). If a chunk's text contains one of these markers it is almost
# certainly a hallucination of a near-silent segment, so we drop the chunk.
HALLUCINATION_MARKERS = (
    "www.", "http://", "https://", ".gov", ".com", ".org",
    "for more information", "thanks for watching", "thank you for watching",
    "subscribe", "see you next time", "see you in the next",
    "don't forget to", "cdc.gov", "fema", "stay tuned",
)

_client = None


def _get_client():
    """Return a cached OpenAI client, creating it on first use."""
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        _client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=60)
    return _client


def transcribe_audio_b64(audio_b64, fmt, language=None):
    """Transcribe one base64-encoded audio chunk.

    ``language`` is an optional ISO-639-1 code (e.g. "es", "zh", "hi"). When set,
    Whisper is told the language instead of guessing per chunk — far more accurate
    and consistent for non-English speech. When ``None``/empty, Whisper auto-detects.

    Returns ``{"text": "..."}`` on success, or ``{"text": "", "note": "<reason>"}``
    for silence / noise / recoverable errors. Never raises — a single bad chunk
    must not break a long recording.
    """
    fmt = (fmt or "").lower().lstrip(".")
    if fmt not in ALLOWED_FORMATS:
        fmt = "webm"

    try:
        raw = base64.b64decode(audio_b64)
    except Exception:
        logger.warning("transcribe: base64 decode failed")
        return {"text": "", "note": "decode_error"}

    if len(raw) < MIN_BLOB_BYTES:
        return {"text": "", "note": "too_small"}

    # Windows-safe temp file: write and close it before handing the path to the
    # SDK, otherwise the open handle holds an exclusive lock and the read fails.
    fd, tmp_path = tempfile.mkstemp(suffix="." + fmt)
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(raw)

        kwargs = {
            "model": settings.OPENAI_TRANSCRIBE_MODEL,
            "file": None,  # set below
        }
        language = (language or "").strip().lower()
        if language and language != "auto":
            kwargs["language"] = language

        # Bias digit formatting. Only for English / auto-detect, since an English
        # prompt can degrade transcription of other languages.
        if language in ("", "auto", "en"):
            kwargs["prompt"] = TRANSCRIBE_PROMPT

        with open(tmp_path, "rb") as audio_file:
            kwargs["file"] = audio_file
            resp = _get_client().audio.transcriptions.create(**kwargs)
    except Exception:
        logger.exception("transcribe: OpenAI call failed")
        return {"text": "", "note": "transcribe_error"}
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    text = (getattr(resp, "text", "") or "").strip()
    low = text.lower().strip(" .,!?")
    if not low or low in FILTERED_PHRASES:
        return {"text": "", "note": "filtered"}
    for marker in HALLUCINATION_MARKERS:
        if marker in low:
            return {"text": "", "note": "hallucination"}

    return {"text": text}


_SUMMARY_SYSTEM_PROMPT = """You are Aira, a careful medical-visit explainer. You are given a \
transcript of a patient's doctor visit. Produce a clear, plain-language "Visit Summary" \
that a patient with no medical background can understand (about a 6th-grade reading level).

Use EXACTLY these Markdown section headers, in this order:

## Key points
## Diagnoses
## Medications & dosages
## Instructions
## Follow-up / next steps
## Questions to ask at the next visit

Rules:
- Write the ENTIRE summary in the SAME language the transcript is in. If the visit was in \
Spanish, answer in Spanish; if in Chinese, answer in Chinese; and so on. Keep the section \
headers in that language too (translate them naturally).
- The transcript is auto-generated and may be garbled or misspelled. When the intended meaning \
is clear, gently correct it instead of copying the error (e.g. Tagalog "Duminum ng paracetamol" \
clearly means "Uminom ng paracetamol" = "take paracetamol", so write "Take paracetamol"). Never \
copy obviously broken words verbatim — interpret them.
- Write key points as complete, natural sentences a patient can act on — not raw fragments.
- For each medication or diagnosis that IS mentioned, add a brief, general one-line explanation \
in parentheses of what it is commonly used for (e.g. "Paracetamol (a common pain and fever \
reliever)"). Keep it general knowledge, clearly informational, and never a personalized dose or \
treatment recommendation.
- Use ONLY information stated in the transcript. Do not invent diagnoses, medications, \
or dosages, and never guess numbers.
- If something is ambiguous or was not clearly stated, write "unclear from the recording" \
(in the transcript's language) under the relevant section rather than guessing.
- If a section has no relevant content, say "None mentioned" in the transcript's language.
- NUMBERS: the transcript is auto-generated and may spell out or split numbers across words. \
Reconstruct and format them cleanly:
  - Phone numbers as (XXX) XXX-XXXX (or the local convention for the transcript's language).
  - Dates as a clear full date (e.g., June 20, 2026); resolve relative dates like "in two weeks" \
to a concrete date when the visit date is known, otherwise keep the relative phrasing.
  - Times as e.g. 2:30 PM.
  - Dosages with the number, unit, and frequency (e.g., 10 mg, twice a day).
  Only reformat numbers actually present in the transcript — never invent or guess a digit. \
If a phone number or date is clearly incomplete or garbled, say so rather than fabricating it.
- Keep bullets short and concrete. This is a memory aid, not medical advice."""


def summarize_visit(transcript):
    """Generate a structured Visit Summary from a full transcript.

    Returns ``{"summary": "..."}``. Raises on API failure so the view can map it
    to a 502 (the transcript itself is already saved client-side).
    """
    transcript = (transcript or "").strip()
    if not transcript:
        return {"summary": ""}

    resp = _get_client().chat.completions.create(
        model=settings.OPENAI_SUMMARY_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": transcript[:24000]},
        ],
    )
    return {"summary": resp.choices[0].message.content or ""}
