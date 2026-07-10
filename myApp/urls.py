from django.urls import path

from . import views
from . import pilot_dashboard_views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('our-story/', views.our_story, name='our_story'),
    path('faq/', views.faq, name='faq'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('contact/', views.contact, name='contact'),

    # "Record & remember" API
    path('api/voice/transcribe/', views.voice_transcribe, name='voice_transcribe'),
    path('api/visit/summarize/', views.visit_summarize, name='visit_summarize'),
    path('api/visit/email-summary/', views.visit_email_summary, name='visit_email_summary'),
    path('api/pilot-survey/', views.pilot_survey_submit, name='pilot_survey_submit'),

    # Custom pilot dashboard (not Django admin)
    path('pilot-dashboard/login/', pilot_dashboard_views.pilot_dashboard_login, name='pilot_dashboard_login'),
    path('pilot-dashboard/logout/', pilot_dashboard_views.pilot_dashboard_logout, name='pilot_dashboard_logout'),
    path('pilot-dashboard/', pilot_dashboard_views.pilot_dashboard_overview, name='pilot_dashboard_overview'),
    path('pilot-dashboard/responses/', pilot_dashboard_views.pilot_dashboard_responses, name='pilot_dashboard_responses'),
    path('pilot-dashboard/responses/<int:response_id>/', pilot_dashboard_views.pilot_dashboard_detail, name='pilot_dashboard_detail'),
    path('pilot-dashboard/export/excel/', pilot_dashboard_views.pilot_dashboard_export_excel, name='pilot_dashboard_export_excel'),
    path('pilot-dashboard/export/pdf/', pilot_dashboard_views.pilot_dashboard_export_pdf, name='pilot_dashboard_export_pdf'),
    path('pilot-dashboard/responses/<int:response_id>/pdf/', pilot_dashboard_views.pilot_dashboard_export_pdf_detail, name='pilot_dashboard_export_pdf_detail'),
    path('pilot-dashboard/print/', pilot_dashboard_views.pilot_dashboard_print, name='pilot_dashboard_print'),
]
