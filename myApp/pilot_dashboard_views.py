import hmac
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .models import PilotSurveyResponse
from .pilot_dashboard import (
    build_excel,
    build_pdf_detail,
    build_pdf_report,
    compute_stats,
    export_filename,
    filter_queryset,
    response_rows,
)
SESSION_KEY = 'pilot_dashboard_authenticated'


def _credentials_configured() -> bool:
    return bool(settings.PILOT_DASHBOARD_USERNAME and settings.PILOT_DASHBOARD_PASSWORD)


def pilot_dashboard_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get(SESSION_KEY):
            return redirect('pilot_dashboard_login')
        return view_func(request, *args, **kwargs)

    return wrapper


def _get_filtered_queryset(request):
    role = (request.GET.get('role') or '').strip()
    q = (request.GET.get('q') or '').strip()
    if role not in {PilotSurveyResponse.ROLE_PATIENT, PilotSurveyResponse.ROLE_CAREGIVER, PilotSurveyResponse.ROLE_NURSE}:
        role = ''
    return filter_queryset(PilotSurveyResponse.objects.all(), role=role or None, q=q or None)


@require_http_methods(['GET', 'POST'])
def pilot_dashboard_login(request):
    if request.session.get(SESSION_KEY):
        return redirect('pilot_dashboard_overview')

    error = None
    if request.method == 'POST':
        if not _credentials_configured():
            error = 'Dashboard login is not configured. Set PILOT_DASHBOARD_USERNAME and PILOT_DASHBOARD_PASSWORD.'
        else:
            username = (request.POST.get('username') or '').strip()
            password = request.POST.get('password') or ''
            valid_user = hmac.compare_digest(username, settings.PILOT_DASHBOARD_USERNAME)
            valid_pass = hmac.compare_digest(password, settings.PILOT_DASHBOARD_PASSWORD)
            if valid_user and valid_pass:
                request.session[SESSION_KEY] = True
                request.session.set_expiry(60 * 60 * 8)
                return redirect('pilot_dashboard_overview')
            error = 'Invalid username or password.'

    return render(request, 'myApp/pilot_dashboard/login.html', {'error': error})


@require_GET
def pilot_dashboard_logout(request):
    request.session.pop(SESSION_KEY, None)
    messages.success(request, 'You have been signed out of the pilot dashboard.')
    return redirect('pilot_dashboard_login')


@pilot_dashboard_required
@require_GET
def pilot_dashboard_overview(request):
    queryset = PilotSurveyResponse.objects.all()
    stats = compute_stats(queryset)
    recent = queryset[:8]
    return render(request, 'myApp/pilot_dashboard/overview.html', {
        'active_nav': 'overview',
        'stats': stats,
        'recent': recent,
        'role_filter': '',
        'search_query': '',
    })


@pilot_dashboard_required
@require_GET
def pilot_dashboard_responses(request):
    queryset = _get_filtered_queryset(request)
    role_filter = (request.GET.get('role') or '').strip()
    search_query = (request.GET.get('q') or '').strip()
    return render(request, 'myApp/pilot_dashboard/responses.html', {
        'active_nav': 'responses',
        'responses': queryset,
        'role_filter': role_filter,
        'search_query': search_query,
        'role_choices': PilotSurveyResponse.ROLE_CHOICES,
        'total_count': queryset.count(),
    })


@pilot_dashboard_required
@require_GET
def pilot_dashboard_detail(request, response_id: int):
    response = get_object_or_404(PilotSurveyResponse, pk=response_id)
    return render(request, 'myApp/pilot_dashboard/detail.html', {
        'active_nav': 'responses',
        'response': response,
        'answer_rows': response_rows(response),
    })


@pilot_dashboard_required
@require_GET
def pilot_dashboard_export_excel(request):
    queryset = _get_filtered_queryset(request)
    content = build_excel(queryset)
    filename = export_filename('airamed_pilot_responses', 'xlsx')
    response = HttpResponse(
        content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@pilot_dashboard_required
@require_GET
def pilot_dashboard_export_pdf(request):
    queryset = _get_filtered_queryset(request)
    content = build_pdf_report(queryset)
    filename = export_filename('airamed_pilot_report', 'pdf')
    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@pilot_dashboard_required
@require_GET
def pilot_dashboard_export_pdf_detail(request, response_id: int):
    survey = get_object_or_404(PilotSurveyResponse, pk=response_id)
    content = build_pdf_detail(survey)
    filename = export_filename(f'airamed_pilot_response_{survey.id}', 'pdf')
    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@pilot_dashboard_required
@require_GET
def pilot_dashboard_print(request):
    queryset = _get_filtered_queryset(request)
    printable = [
        {
            'id': item.id,
            'role': item.get_role_display(),
            'created_at': item.created_at,
            'rows': response_rows(item),
        }
        for item in queryset
    ]
    return render(request, 'myApp/pilot_dashboard/print.html', {
        'responses': printable,
        'stats': compute_stats(queryset),
        'role_filter': (request.GET.get('role') or '').strip(),
        'search_query': (request.GET.get('q') or '').strip(),
    })
