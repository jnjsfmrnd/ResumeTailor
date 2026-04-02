from django.contrib import admin

from .models import CoverLetterDraft, GenerationRun, ResumeSection, ResumeSession


@admin.register(ResumeSession)
class ResumeSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "generation_mode", "credential_mode", "created_at"]
    list_filter = ["status", "generation_mode", "credential_mode"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(ResumeSection)
class ResumeSectionAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "section_key", "order_index", "review_status"]
    list_filter = ["review_status"]
    readonly_fields = ["id"]


@admin.register(CoverLetterDraft)
class CoverLetterDraftAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "review_status"]
    list_filter = ["review_status"]
    readonly_fields = ["id"]


@admin.register(GenerationRun)
class GenerationRunAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "model_name", "status", "started_at", "duration_ms"]
    list_filter = ["status", "credential_mode"]
    readonly_fields = ["id"]
