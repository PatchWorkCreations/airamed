from django.contrib import admin

from .models import PilotSurveyResponse, PlannerLead


@admin.register(PilotSurveyResponse)
class PilotSurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    readonly_fields = ('role', 'responses', 'created_at')


@admin.register(PlannerLead)
class PlannerLeadAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'lead', 'source', 'tag', 'submitted_at', 'created_at')
    list_filter = ('tag', 'source', 'created_at')
    search_fields = ('email', 'lead', 'source', 'tag')
    readonly_fields = ('email', 'source', 'lead', 'tag', 'submitted_at', 'created_at')
