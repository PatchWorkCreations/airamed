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
