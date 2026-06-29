from django.urls import path

from . import views

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
]
