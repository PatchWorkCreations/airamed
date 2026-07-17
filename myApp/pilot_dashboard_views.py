import hmac
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import ClientOrganization, PilotSurveyResponse
from .onboarding import TOTAL_STEPS, answers_by_step
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


# --- Client onboarding pipeline -------------------------------------------

STATUS_BADGE_CLASSES = {
    ClientOrganization.STATUS_INVITED: 'invited',
    ClientOrganization.STATUS_INTAKE_STARTED: 'progress',
    ClientOrganization.STATUS_INTAKE_COMPLETE: 'complete',
    ClientOrganization.STATUS_KICKOFF_SCHEDULED: 'kickoff',
    ClientOrganization.STATUS_ACTIVE_PILOT: 'active',
    ClientOrganization.STATUS_EVALUATION: 'evaluation',
    ClientOrganization.STATUS_DECISION: 'decision',
}

STATUS_ORDER = [status for status, _ in ClientOrganization.STATUS_CHOICES]


def _client_row(request, org: ClientOrganization) -> dict:
    submission = getattr(org, 'onboarding', None)
    if submission is None:
        progress = 'Not started'
    elif submission.is_complete:
        progress = 'Completed'
    else:
        progress = f'Step {submission.current_step} of {TOTAL_STEPS}'
    return {
        'org': org,
        'progress': progress,
        'badge_class': STATUS_BADGE_CLASSES.get(org.status, 'invited'),
        'invite_url': request.build_absolute_uri(reverse('onboarding_resume', args=[org.invite_token])),
    }


@pilot_dashboard_required
@require_GET
def pilot_dashboard_clients(request):
    orgs = ClientOrganization.objects.select_related('onboarding').all()
    status_filter = (request.GET.get('status') or '').strip()
    if status_filter in STATUS_ORDER:
        orgs = orgs.filter(status=status_filter)

    all_orgs = ClientOrganization.objects.all()
    onboarding_statuses = [ClientOrganization.STATUS_INVITED, ClientOrganization.STATUS_INTAKE_STARTED]
    stats = {
        'total': all_orgs.count(),
        'in_onboarding': all_orgs.filter(status__in=onboarding_statuses).count(),
        'intake_complete': all_orgs.filter(status=ClientOrganization.STATUS_INTAKE_COMPLETE).count(),
        'active': all_orgs.filter(status=ClientOrganization.STATUS_ACTIVE_PILOT).count(),
    }
    return render(request, 'myApp/pilot_dashboard/clients.html', {
        'active_nav': 'clients',
        'rows': [_client_row(request, org) for org in orgs],
        'stats': stats,
        'status_filter': status_filter,
        'status_choices': ClientOrganization.STATUS_CHOICES,
        'evergreen_url': request.build_absolute_uri(reverse('onboarding_start')),
    })


@pilot_dashboard_required
@require_POST
def pilot_dashboard_client_new(request):
    name = (request.POST.get('name') or '').strip()
    if not name:
        messages.success(request, 'Please provide the organization name.')
        return redirect('pilot_dashboard_clients')
    org = ClientOrganization.objects.create(
        name=name,
        department=(request.POST.get('department') or '').strip(),
        primary_contact_name=(request.POST.get('contact_name') or '').strip(),
        primary_contact_email=(request.POST.get('contact_email') or '').strip(),
        source=ClientOrganization.SOURCE_INVITED,
        status=ClientOrganization.STATUS_INVITED,
    )
    messages.success(request, f'{org.name} added — copy their invite link below and send it over.')
    return redirect('pilot_dashboard_client_detail', client_id=org.pk)


@pilot_dashboard_required
@require_GET
def pilot_dashboard_client_detail(request, client_id: int):
    org = get_object_or_404(ClientOrganization, pk=client_id)
    submission = getattr(org, 'onboarding', None)
    current_index = STATUS_ORDER.index(org.status)
    pipeline = [
        {
            'value': value,
            'label': label,
            'state': 'done' if i < current_index else ('current' if i == current_index else 'todo'),
        }
        for i, (value, label) in enumerate(ClientOrganization.STATUS_CHOICES)
    ]
    next_status = STATUS_ORDER[current_index + 1] if current_index + 1 < len(STATUS_ORDER) else None
    return render(request, 'myApp/pilot_dashboard/client_detail.html', {
        'active_nav': 'clients',
        'row': _client_row(request, org),
        'submission': submission,
        'answer_groups': answers_by_step(submission.responses) if submission and submission.responses else [],
        'pipeline': pipeline,
        'next_status': next_status,
        'next_status_label': dict(ClientOrganization.STATUS_CHOICES).get(next_status, ''),
        'status_choices': ClientOrganization.STATUS_CHOICES,
    })


@pilot_dashboard_required
@require_POST
def pilot_dashboard_client_status(request, client_id: int):
    org = get_object_or_404(ClientOrganization, pk=client_id)
    new_status = (request.POST.get('status') or '').strip()
    if new_status in STATUS_ORDER:
        org.status = new_status
        org.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'{org.name} moved to “{org.get_status_display()}”.')
    return redirect('pilot_dashboard_client_detail', client_id=org.pk)


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
