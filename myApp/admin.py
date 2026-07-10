from django.contrib import admin

from .models import PilotSurveyResponse


@admin.register(PilotSurveyResponse)
class PilotSurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    readonly_fields = ('role', 'responses', 'created_at')
