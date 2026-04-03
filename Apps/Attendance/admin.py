"""attendance/admin.py"""

from django.contrib import admin
from django.utils.html import format_html
from .models import AttendanceSession, AttendanceRecord, AttendanceSummary


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    fields = ('enrollment', 'status', 'excuse_reason', 'notes')
    show_change_link = True


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = (
        'course', 'date', 'session_type', 'topic',
        'present_count', 'absent_count', 'attendance_rate_display', 'is_locked',
    )
    list_filter = ('session_type', 'is_locked', 'course__semester', 'date')
    search_fields = ('course__course_code', 'topic')
    ordering = ('-date',)
    date_hierarchy = 'date'
    inlines = [AttendanceRecordInline]
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Attendance Rate')
    def attendance_rate_display(self, obj):
        rate = obj.attendance_rate
        color = '#198754' if rate >= 75 else '#ffc107' if rate >= 50 else '#dc3545'
        return format_html('<span style="color:{};">{:.1f}%</span>', color, rate)

    actions = ['lock_sessions', 'unlock_sessions']

    @admin.action(description='Lock selected sessions')
    def lock_sessions(self, request, queryset):
        queryset.update(is_locked=True)

    @admin.action(description='Unlock selected sessions')
    def unlock_sessions(self, request, queryset):
        queryset.update(is_locked=False)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        'get_student', 'get_course', 'get_date',
        'status_badge', 'excuse_reason',
    )
    list_filter = ('status', 'session__course', 'session__date')
    search_fields = (
        'enrollment__student__user__first_name',
        'enrollment__student__user__last_name',
        'enrollment__student__student_id',
        'session__course__course_code',
    )
    ordering = ('-session__date',)
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Student')
    def get_student(self, obj):
        return obj.enrollment.student.user.get_full_name()

    @admin.display(description='Course')
    def get_course(self, obj):
        return obj.session.course.course_code

    @admin.display(description='Date')
    def get_date(self, obj):
        return obj.session.date

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'present': '#198754', 'absent': '#dc3545',
            'late': '#ffc107', 'excused': '#0dcaf0', 'remote': '#0d6efd',
        }
        return format_html(
            '<span style="color:{};">{}</span>',
            colors.get(obj.status, '#6c757d'), obj.get_status_display()
        )


@admin.register(AttendanceSummary)
class AttendanceSummaryAdmin(admin.ModelAdmin):
    list_display = (
        'enrollment', 'total_sessions', 'present_count',
        'absent_count', 'attendance_percentage', 'last_updated',
    )
    readonly_fields = (
        'total_sessions', 'present_count', 'absent_count',
        'late_count', 'excused_count', 'remote_count',
        'attendance_percentage', 'last_updated',
    )
    ordering = ('enrollment',)