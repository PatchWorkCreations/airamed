from django.db import models


class PilotSurveyResponse(models.Model):
    ROLE_PATIENT = 'patient'
    ROLE_CAREGIVER = 'caregiver'
    ROLE_NURSE = 'nurse'

    ROLE_CHOICES = [
        (ROLE_PATIENT, 'Patient'),
        (ROLE_CAREGIVER, 'Family / Caregiver'),
        (ROLE_NURSE, 'Nurse / Staff'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    responses = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_role_display()} — {self.created_at:%Y-%m-%d %H:%M}'


class PlannerLead(models.Model):
    DEFAULT_TAG = 'Team Unstoppable / 2027 Planner lead'

    email = models.EmailField(db_index=True)
    source = models.CharField(max_length=255, blank=True, default='')
    lead = models.CharField(max_length=255, blank=True, default='')
    tag = models.CharField(max_length=255, default=DEFAULT_TAG)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Planner lead'
        verbose_name_plural = 'Planner leads'

    def __str__(self):
        return f'{self.email} — {self.created_at:%Y-%m-%d %H:%M}'
