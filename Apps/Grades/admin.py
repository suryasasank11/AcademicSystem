"""grades/admin.py"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Grade, GradeComponent, GradeHistory


class GradeHistoryInline(admin.TabularInline):
    model = GradeHistory
    extra = 0
    readonly_fields = (
        'changed_by', 'old_numeric_score', 'new_numeric_score',
        'old_letter_grade', 'new_letter_grade', 'reason', 'changed_at',
    )
    can_delete = False


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = (
        'get_student', 'get_course', 'numeric_score',
        'letter_grade_badge', 'grade_points', 'is_finalized', 'graded_at',
    )
    list_filter = ('is_finalized', 'letter_grade', 'enrollment__course__semester')
    search_fields = (
        'enrollment__student__student_id',
        'enrollment__student__user__first_name',
        'enrollment__student__user__last_name',
        'enrollment__course__course_code',
    )
    ordering = ('-graded_at',)
    readonly_fields = ('grade_points', 'graded_at', 'finalized_at', 'created_at', 'updated_at')
    inlines = [GradeHistoryInline]

    @admin.display(description='Student', ordering='enrollment__student__user__last_name')
    def get_student(self, obj):
        return obj.enrollment.student.user.get_full_name()

    @admin.display(description='Course', ordering='enrollment__course__course_code')
    def get_course(self, obj):
        return obj.enrollment.course.course_code

    @admin.display(description='Letter Grade')
    def letter_grade_badge(self, obj):
        if not obj.letter_grade:
            return '—'
        colors = {'A': '#198754', 'B': '#0d6efd', 'C': '#ffc107', 'D': '#fd7e14', 'F': '#dc3545'}
        color = colors.get(obj.letter_grade[0], '#6c757d')
        return format_html(
            '<strong style="color:{};">{}</strong>', color, obj.letter_grade
        )

    actions = ['finalize_selected_grades']

    @admin.action(description='Finalize selected grades')
    def finalize_selected_grades(self, request, queryset):
        updated = queryset.filter(is_finalized=False).update(is_finalized=True)
        self.message_user(request, f'{updated} grade(s) finalized.')


@admin.register(GradeComponent)
class GradeComponentAdmin(admin.ModelAdmin):
    list_display = ('course', 'name', 'component_type', 'weight', 'max_score', 'order')
    list_filter = ('component_type', 'course__semester')
    search_fields = ('name', 'course__course_code')
    ordering = ('course', 'order')


@admin.register(GradeHistory)
class GradeHistoryAdmin(admin.ModelAdmin):
    list_display = ('grade', 'changed_by', 'old_letter_grade', 'new_letter_grade', 'changed_at')
    readonly_fields = (
        'grade', 'changed_by', 'old_numeric_score', 'new_numeric_score',
        'old_letter_grade', 'new_letter_grade', 'reason', 'changed_at',
    )
    ordering = ('-changed_at',)