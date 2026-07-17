import uuid

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


class ClientOrganization(models.Model):
    """A health system client moving through the pilot pipeline."""

    STATUS_INVITED = 'invited'
    STATUS_INTAKE_STARTED = 'intake_started'
    STATUS_INTAKE_COMPLETE = 'intake_complete'
    STATUS_KICKOFF_SCHEDULED = 'kickoff_scheduled'
    STATUS_ACTIVE_PILOT = 'active_pilot'
    STATUS_EVALUATION = 'evaluation'
    STATUS_DECISION = 'decision'

    STATUS_CHOICES = [
        (STATUS_INVITED, 'Invited'),
        (STATUS_INTAKE_STARTED, 'Onboarding in progress'),
        (STATUS_INTAKE_COMPLETE, 'Onboarding complete'),
        (STATUS_KICKOFF_SCHEDULED, 'Kickoff scheduled'),
        (STATUS_ACTIVE_PILOT, 'Active pilot'),
        (STATUS_EVALUATION, 'Evaluation'),
        (STATUS_DECISION, 'Go / no-go decision'),
    ]

    SOURCE_INVITED = 'invited'
    SOURCE_SELF_SERVE = 'self_serve'

    SOURCE_CHOICES = [
        (SOURCE_INVITED, 'Invited by AiraMed'),
        (SOURCE_SELF_SERVE, 'Self-serve link'),
    ]

    name = models.CharField(max_length=255)
    department = models.CharField(max_length=255, blank=True, default='')
    primary_contact_name = models.CharField(max_length=255, blank=True, default='')
    primary_contact_email = models.EmailField(blank=True, default='')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_INVITED)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_INVITED)
    invite_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Client organization'
        verbose_name_plural = 'Client organizations'

    def __str__(self):
        return f'{self.name} ({self.get_status_display()})'


class OnboardingSubmission(models.Model):
    """Saved answers from the client onboarding wizard (save & resume)."""

    organization = models.OneToOneField(
        ClientOrganization,
        on_delete=models.CASCADE,
        related_name='onboarding',
    )
    responses = models.JSONField(default=dict, blank=True)
    current_step = models.PositiveSmallIntegerField(default=1)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    def __str__(self):
        state = 'complete' if self.is_complete else f'step {self.current_step}'
        return f'{self.organization.name} onboarding — {state}'
