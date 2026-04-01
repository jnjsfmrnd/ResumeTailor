"""Domain models for resume sessions.

Contracts:
  - session-schema v1.0.0
  - section-output-schema v1.0.0
  - cover-letter-draft-schema v1.0.0
  - generation-service-interface v1.0.0

Any field change here requires a corresponding contract version bump in
docs/contracts/CONTRACT-VERSION.md (platform lead approval required).
"""

import uuid

from django.db import models


class ResumeSession(models.Model):
    """Top-level session tracking a single tailoring workflow.

    Contracts: docs/contracts/session-schema.md v1.0.0
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        INGESTING = "ingesting", "Ingesting"
        GENERATING = "generating", "Generating"
        REVIEW = "review", "Review"
        EXPORTING = "exporting", "Exporting"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    class GenerationMode(models.TextChoices):
        RESUME_ONLY = "resume_only", "Resume only"
        RESUME_AND_COVER_LETTER = "resume_and_cover_letter", "Resume and cover letter"

    class CredentialMode(models.TextChoices):
        APP_KEY = "app_key", "App key"
        USER_KEY = "user_key", "User key"

    class OutputArtifactType(models.TextChoices):
        SINGLE_PDF = "single_pdf", "Single PDF"
        DUAL_PDF = "dual_pdf", "Dual PDF"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    source_pdf_path = models.TextField()
    output_pdf_path = models.TextField(blank=True, default="")
    output_artifact_type = models.CharField(
        max_length=20,
        choices=OutputArtifactType.choices,
        default=OutputArtifactType.SINGLE_PDF,
    )
    generation_mode = models.CharField(
        max_length=30,
        choices=GenerationMode.choices,
        default=GenerationMode.RESUME_ONLY,
    )
    credential_mode = models.CharField(
        max_length=10,
        choices=CredentialMode.choices,
        default=CredentialMode.APP_KEY,
    )
    selected_model = models.CharField(max_length=100, default="gpt-5.1")
    job_description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ResumeSession({self.id}, {self.status})"


class ResumeSection(models.Model):
    """A parsed section from the source PDF, with tailoring state.

    Contracts: docs/contracts/section-output-schema.md v1.0.0
    """

    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ResumeSession, on_delete=models.CASCADE, related_name="sections"
    )
    section_key = models.CharField(max_length=100)
    order_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField()
    # Bounding box stored as individual floats (PDF user-space units, bottom-left origin)
    bbox_x0 = models.FloatField()
    bbox_y0 = models.FloatField()
    bbox_x1 = models.FloatField()
    bbox_y1 = models.FloatField()
    original_content = models.TextField()
    tailored_content = models.TextField(blank=True, default="")
    user_edited_content = models.TextField(blank=True, default="")
    review_status = models.CharField(
        max_length=10,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )

    class Meta:
        ordering = ["order_index"]
        unique_together = [("session", "section_key"), ("session", "order_index")]

    @property
    def resolved_content(self) -> str:
        """Return content using contract-defined precedence: user_edited > tailored > original."""
        if self.user_edited_content:
            return self.user_edited_content
        if self.tailored_content:
            return self.tailored_content
        return self.original_content

    def __str__(self) -> str:
        return f"ResumeSection({self.session_id}, {self.section_key})"


class CoverLetterDraft(models.Model):
    """Cover letter draft for resume_and_cover_letter sessions only.

    Contracts: docs/contracts/cover-letter-draft-schema.md v1.0.0

    Invariant: must not exist when session.generation_mode == resume_only.
    """

    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(
        ResumeSession, on_delete=models.CASCADE, related_name="cover_letter_draft"
    )
    original_grounding_summary = models.TextField()
    tailored_content = models.TextField()
    user_edited_content = models.TextField(blank=True, default="")
    review_status = models.CharField(
        max_length=10,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )

    @property
    def resolved_content(self) -> str:
        """Return content using contract-defined precedence: user_edited > tailored."""
        if self.user_edited_content:
            return self.user_edited_content
        return self.tailored_content

    def __str__(self) -> str:
        return f"CoverLetterDraft({self.session_id})"


class GenerationRun(models.Model):
    """Record of a single generation attempt.

    Contracts: docs/contracts/generation-service-interface.md v1.0.0

    Invariant: error_summary must never contain resume text, cover letter text,
    or job description text.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        TIMED_OUT = "timed_out", "Timed out"

    class ErrorCode(models.TextChoices):
        TIMEOUT_USER_KEY = "timeout_user_key", "Timeout (user key)"
        TIMEOUT_APP_KEY = "timeout_app_key", "Timeout (app key)"
        UNSUPPORTED_PDF = "unsupported_pdf", "Unsupported PDF"
        STRUCTURED_OUTPUT_INVALID = "structured_output_invalid", "Structured output invalid"
        MODEL_UNAVAILABLE = "model_unavailable", "Model unavailable"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ResumeSession, on_delete=models.CASCADE, related_name="generation_runs"
    )
    model_name = models.CharField(max_length=100)
    credential_mode = models.CharField(
        max_length=10, choices=ResumeSession.CredentialMode.choices
    )
    prompt_version = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    error_code = models.CharField(
        max_length=40, choices=ErrorCode.choices, blank=True, default=""
    )
    error_summary = models.TextField(blank=True, default="")
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"GenerationRun({self.session_id}, {self.status})"
