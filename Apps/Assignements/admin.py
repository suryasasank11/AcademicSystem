"""assignments/admin.py"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Assignment, AssignmentSubmission, SubmissionComment


class SubmissionInline(admin.TabularInline):
    model = AssignmentSubmission
    extra = 0
    fields = ('student', 'status', 'score', 'is_graded', 'submitted_at')
    readonly_fields = ('submitted_at',)
    show_change_link = True


class CommentInline(admin.TabularInline):
    model = SubmissionComment
    extra = 0
    fields = ('author', 'content', 'is_private', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'course', 'assignment_type',
        'max_score', 'due_date', 'status_badge',
        'submission_count', 'pending_display',
    )
    list_filter = ('status', 'assignment_type', 'course__semester')
    search_fields = ('title', 'course__course_code', 'created_by__first_name')
    ordering = ('due_date',)
    date_hierarchy = 'due_date'
    inlines = [SubmissionInline]
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d', 'published': '#198754',
            'closed': '#0d6efd', 'graded': '#6f42c1',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;">{}</span>',
            colors.get(obj.status, '#6c757d'), obj.get_status_display()
        )

    @admin.display(description='Submissions')
    def submission_count(self, obj):
        return obj.submissions.count()

    @admin.display(description='Pending')
    def pending_display(self, obj):
        pending = obj.pending_grading_count
        if pending:
            return format_html('<span style="color:#dc3545;font-weight:bold;">{}</span>', pending)
        return format_html('<span style="color:#198754;">0</span>')

    actions = ['publish_assignments', 'close_assignments']

    @admin.action(description='Publish selected assignments')
    def publish_assignments(self, request, queryset):
        updated = queryset.filter(status='draft').update(status='published')
        self.message_user(request, f'{updated} assignment(s) published.')

    @admin.action(description='Close selected assignments')
    def close_assignments(self, request, queryset):
        updated = queryset.exclude(status='closed').update(status='closed')
        self.message_user(request, f'{updated} assignment(s) closed.')


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        'student', 'assignment', 'status',
        'score', 'is_graded', 'is_late', 'submitted_at',
    )
    list_filter = ('status', 'is_graded', 'is_late')
    search_fields = (
        'student__student_id',
        'student__user__first_name', 'student__user__last_name',
        'assignment__title',
    )
    ordering = ('-submitted_at',)
    readonly_fields = ('submitted_at', 'graded_at', 'created_at', 'updated_at')
    inlines = [CommentInline]

    actions = ['mark_as_graded']

    @admin.action(description='Mark selected submissions as graded')
    def mark_as_graded(self, request, queryset):
        updated = queryset.update(is_graded=True, status='graded')
        self.message_user(request, f'{updated} submission(s) marked as graded.')


@admin.register(SubmissionComment)
class SubmissionCommentAdmin(admin.ModelAdmin):
    list_display = ('submission', 'author', 'is_private', 'created_at')
    list_filter = ('is_private',)
    readonly_fields = ('created_at', 'updated_at')