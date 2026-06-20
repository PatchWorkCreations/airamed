from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('faq/', views.faq, name='faq'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('contact/', views.contact, name='contact'),

    # "Record & remember" API
    path('api/voice/transcribe/', views.voice_transcribe, name='voice_transcribe'),
    path('api/visit/summarize/', views.visit_summarize, name='visit_summarize'),
]
