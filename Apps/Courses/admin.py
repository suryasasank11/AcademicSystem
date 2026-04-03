"""courses/admin.py"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Course, Enrollment, Announcement


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    fields = ('student', 'status', 'enrollment_date')
    readonly_fields = ('enrollment_date',)
    show_change_link = True


class AnnouncementInline(admin.TabularInline):
    model = Announcement
    extra = 0
    fields = ('title', 'priority', 'is_pinned', 'publish_at')
    readonly_fields = ('publish_at',)
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        'course_code', 'title', 'professor', 'department',
        'semester', 'academic_year', 'enrolled_display',
        'status_badge', 'is_active',
    )
    list_filter = ('status', 'semester', 'academic_year', 'department', 'delivery_mode')
    search_fields = ('course_code', 'title', 'professor__first_name', 'professor__last_name')
    ordering = ('-academic_year', 'semester', 'course_code')
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at')
    inlines = [EnrollmentInline, AnnouncementInline]

    fieldsets = (
        ('Course Info', {'fields': ('course_code', 'title', 'description', 'syllabus')}),
        ('People', {'fields': ('professor', 'department')}),
        ('Academic Period', {'fields': ('academic_year', 'semester', 'start_date', 'end_date')}),
        ('Capacity & Credits', {'fields': ('credits', 'max_students')}),
        ('Schedule', {'fields': ('schedule_days', 'start_time', 'end_time', 'room', 'delivery_mode', 'meeting_link')}),
        ('Status', {'fields': ('status', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Enrolled')
    def enrolled_display(self, obj):
        count = obj.enrolled_count
        pct = obj.enrollment_percentage
        color = '#198754' if pct < 80 else '#dc3545'
        return format_html(
            '<span style="color:{};">{}/{}</span>',
            color, count, obj.max_students
        )

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {'draft': '#6c757d', 'active': '#198754', 'completed': '#0d6efd', 'cancelled': '#dc3545'}
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            colors.get(obj.status, '#6c757d'), obj.get_status_display()
        )


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'status', 'enrollment_date')
    list_filter = ('status', 'course__semester', 'course__academic_year')
    search_fields = (
        'student__student_id',
        'student__user__first_name', 'student__user__last_name',
        'course__course_code', 'course__title',
    )
    ordering = ('-enrollment_date',)
    list_per_page = 30
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'author', 'priority', 'is_pinned', 'publish_at')
    list_filter = ('priority', 'announcement_type', 'is_pinned', 'course')
    search_fields = ('title', 'course__course_code', 'author__first_name')
    ordering = ('-is_pinned', '-publish_at')
    readonly_fields = ('created_at', 'updated_at')