"""
accounts/admin.py

Django admin configuration for accounts app.
Custom inlines, list displays, search/filter, and actions.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import User, UserRole, Department, StudentProfile, ProfessorProfile


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------
class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Student Profile'
    extra = 0
    fields = (
        'student_id', 'department', 'year_of_study',
        'enrollment_date', 'expected_graduation',
        'gpa', 'status', 'scholarship',
        'emergency_contact_name', 'emergency_contact_phone',
        'notes',
    )
    readonly_fields = ('gpa',)


class ProfessorProfileInline(admin.StackedInline):
    model = ProfessorProfile
    can_delete = False
    verbose_name_plural = 'Professor Profile'
    extra = 0
    fields = (
        'employee_id', 'department', 'rank',
        'specialization', 'office_location', 'office_hours',
        'hire_date', 'website', 'publications', 'is_active',
    )


# ---------------------------------------------------------------------------
# User Admin
# ---------------------------------------------------------------------------
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # List view
    list_display = (
        'email', 'get_full_name', 'role_badge',
        'is_active', 'is_staff', 'date_joined',
    )
    list_filter = ('role', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('last_name', 'first_name')
    list_per_page = 30
    date_hierarchy = 'date_joined'

    # Detail view
    fieldsets = (
        (_('Login Info'), {
            'fields': ('email', 'password')
        }),
        (_('Personal Info'), {
            'fields': (
                'first_name', 'last_name', 'phone',
                'date_of_birth', 'bio', 'address', 'profile_photo',
            )
        }),
        (_('Role & Permissions'), {
            'fields': (
                'role', 'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions',
            )
        }),
        (_('Important Dates'), {
            'fields': ('date_joined', 'last_login', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('date_joined', 'last_login', 'updated_at')

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name',
                'role', 'password1', 'password2',
            ),
        }),
    )

    # Show inline profile based on role
    def get_inlines(self, request, obj=None):
        if obj is None:
            return []
        if obj.role == UserRole.STUDENT:
            return [StudentProfileInline]
        elif obj.role == UserRole.PROFESSOR:
            return [ProfessorProfileInline]
        return []

    @admin.display(description='Role')
    def role_badge(self, obj):
        colors = {
            'admin': '#dc3545',
            'professor': '#0d6efd',
            'student': '#198754',
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;">{}</span>',
            color, obj.get_role_display()
        )

    # Admin actions
    actions = ['activate_users', 'deactivate_users']

    @admin.action(description='Activate selected users')
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} user(s) activated.')

    @admin.action(description='Deactivate selected users')
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} user(s) deactivated.')


# ---------------------------------------------------------------------------
# Department Admin
# ---------------------------------------------------------------------------
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'head', 'student_count', 'professor_count')
    search_fields = ('code', 'name')
    ordering = ('name',)
    list_per_page = 25

    @admin.display(description='Students')
    def student_count(self, obj):
        return obj.students.count()

    @admin.display(description='Professors')
    def professor_count(self, obj):
        return obj.professors.count()


# ---------------------------------------------------------------------------
# Student Profile Admin
# ---------------------------------------------------------------------------
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        'student_id', 'get_full_name', 'department',
        'year_of_study', 'gpa', 'status', 'scholarship',
    )
    list_filter = ('status', 'year_of_study', 'department', 'scholarship')
    search_fields = (
        'student_id',
        'user__first_name', 'user__last_name', 'user__email',
    )
    ordering = ('student_id',)
    list_per_page = 30
    readonly_fields = ('gpa', 'created_at', 'updated_at')

    fieldsets = (
        ('Student Info', {
            'fields': ('user', 'student_id', 'department', 'year_of_study', 'status')
        }),
        ('Academic', {
            'fields': ('enrollment_date', 'expected_graduation', 'gpa', 'scholarship')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone'),
            'classes': ('collapse',),
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Full Name', ordering='user__last_name')
    def get_full_name(self, obj):
        return obj.user.get_full_name()

    actions = ['update_all_gpas']

    @admin.action(description='Recalculate GPA for selected students')
    def update_all_gpas(self, request, queryset):
        for student in queryset:
            student.update_gpa()
        self.message_user(request, f'GPA updated for {queryset.count()} student(s).')


# ---------------------------------------------------------------------------
# Professor Profile Admin
# ---------------------------------------------------------------------------
@admin.register(ProfessorProfile)
class ProfessorProfileAdmin(admin.ModelAdmin):
    list_display = (
        'employee_id', 'get_full_name', 'department',
        'rank', 'total_courses', 'is_active',
    )
    list_filter = ('rank', 'department', 'is_active')
    search_fields = (
        'employee_id',
        'user__first_name', 'user__last_name', 'user__email',
    )
    ordering = ('employee_id',)
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Full Name', ordering='user__last_name')
    def get_full_name(self, obj):
        return obj.user.get_full_name()

    @admin.display(description='Total Courses')
    def total_courses(self, obj):
        return obj.user.taught_courses.count()