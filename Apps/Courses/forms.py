"""
courses/forms.py

Forms: CourseForm, EnrollmentForm, AnnouncementForm, BulkEnrollForm
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Course, Enrollment, Announcement
from apps.accounts.models import StudentProfile, User, UserRole


def _fc(placeholder=''):
    return {'class': 'form-control', 'placeholder': placeholder}


def _fs():
    return {'class': 'form-select'}


# ---------------------------------------------------------------------------
# Course Form
# ---------------------------------------------------------------------------
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'course_code', 'title', 'description', 'syllabus',
            'professor', 'department',
            'academic_year', 'semester',
            'credits', 'max_students',
            'schedule_days', 'start_time', 'end_time', 'room',
            'delivery_mode', 'meeting_link',
            'start_date', 'end_date', 'status',
        ]
        widgets = {
            'course_code': forms.TextInput(attrs=_fc('e.g. CS-101')),
            'title': forms.TextInput(attrs=_fc('Course title')),
            'description': forms.Textarea(attrs={**_fc('Course description...'), 'rows': 4}),
            'syllabus': forms.FileInput(attrs={'class': 'form-control'}),
            'professor': forms.Select(attrs=_fs()),
            'department': forms.Select(attrs=_fs()),
            'academic_year': forms.Select(attrs=_fs(), choices=[
                ('2024-2025', '2024-2025'),
                ('2025-2026', '2025-2026'),
                ('2026-2027', '2026-2027'),
            ]),
            'semester': forms.Select(attrs=_fs()),
            'credits': forms.NumberInput(attrs={**_fc(), 'min': 1, 'max': 6}),
            'max_students': forms.NumberInput(attrs={**_fc(), 'min': 1, 'max': 500}),
            'schedule_days': forms.TextInput(attrs=_fc('e.g. Mon, Wed, Fri')),
            'start_time': forms.TimeInput(attrs={**_fc(), 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={**_fc(), 'type': 'time'}),
            'room': forms.TextInput(attrs=_fc('e.g. Room 301, Building B')),
            'delivery_mode': forms.Select(attrs=_fs()),
            'meeting_link': forms.URLInput(attrs=_fc('https://zoom.us/...')),
            'start_date': forms.DateInput(attrs={**_fc(), 'type': 'date'}),
            'end_date': forms.DateInput(attrs={**_fc(), 'type': 'date'}),
            'status': forms.Select(attrs=_fs()),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Limit professor choices to users with professor role
        self.fields['professor'].queryset = User.objects.filter(
            role=UserRole.PROFESSOR,
            is_active=True
        ).order_by('last_name', 'first_name')
        self.fields['professor'].label_from_instance = lambda u: u.get_full_name()

        # If the current user is a professor, lock that field
        if user and user.is_professor:
            self.fields['professor'].initial = user
            self.fields['professor'].widget.attrs['disabled'] = True

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        start_time = cleaned.get('start_time')
        end_time = cleaned.get('end_time')

        if start and end and end < start:
            raise ValidationError({'end_date': 'End date must be after start date.'})
        if start_time and end_time and end_time <= start_time:
            raise ValidationError({'end_time': 'End time must be after start time.'})
        return cleaned

    def clean_course_code(self):
        code = self.cleaned_data.get('course_code', '').strip().upper()
        return code


# ---------------------------------------------------------------------------
# Enrollment Form
# ---------------------------------------------------------------------------
class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'status', 'notes']
        widgets = {
            'student': forms.Select(attrs=_fs()),
            'course': forms.Select(attrs=_fs()),
            'status': forms.Select(attrs=_fs()),
            'notes': forms.Textarea(attrs={**_fc('Notes...'), 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = StudentProfile.objects.filter(
            status='active'
        ).select_related('user').order_by('student_id')
        self.fields['student'].label_from_instance = (
            lambda s: f'{s.student_id} — {s.user.get_full_name()}'
        )
        if course:
            self.fields['course'].initial = course
            self.fields['course'].widget.attrs['disabled'] = True

    def clean(self):
        cleaned = super().clean()
        student = cleaned.get('student')
        course = cleaned.get('course')
        if student and course:
            qs = Enrollment.objects.filter(student=student, course=course)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('This student is already enrolled in this course.')
            if course.is_full and cleaned.get('status') == 'enrolled':
                raise ValidationError(
                    f'This course is full ({course.max_students} students). '
                    'Set status to Waitlisted instead.'
                )
        return cleaned


# ---------------------------------------------------------------------------
# Student Self-Enroll Form
# ---------------------------------------------------------------------------
class SelfEnrollForm(forms.Form):
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_active=True, status='active'),
        widget=forms.Select(attrs=_fs()),
        label='Select Course'
    )
    course.label_from_instance = lambda c: (
        f'{c.course_code} — {c.title} '
        f'({c.enrolled_count}/{c.max_students} enrolled)'
    )

    def __init__(self, *args, **kwargs):
        student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        if student:
            already_enrolled = Enrollment.objects.filter(
                student=student,
                status__in=['enrolled', 'waitlisted']
            ).values_list('course_id', flat=True)
            self.fields['course'].queryset = Course.objects.filter(
                is_active=True,
                status='active'
            ).exclude(id__in=already_enrolled)

    def clean_course(self):
        course = self.cleaned_data['course']
        if course.is_full:
            raise ValidationError(
                f'"{course.title}" is currently full. '
                'You will be added to the waitlist.'
            )
        return course


# ---------------------------------------------------------------------------
# Announcement Form
# ---------------------------------------------------------------------------
class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = [
            'title', 'content', 'announcement_type',
            'priority', 'is_pinned', 'send_email',
            'publish_at', 'expires_at',
        ]
        widgets = {
            'title': forms.TextInput(attrs=_fc('Announcement title')),
            'content': forms.Textarea(attrs={**_fc('Write your announcement here...'), 'rows': 6}),
            'announcement_type': forms.Select(attrs=_fs()),
            'priority': forms.Select(attrs=_fs()),
            'is_pinned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'send_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'publish_at': forms.DateTimeInput(attrs={**_fc(), 'type': 'datetime-local'}),
            'expires_at': forms.DateTimeInput(attrs={**_fc(), 'type': 'datetime-local'}),
        }

    def clean(self):
        cleaned = super().clean()
        publish = cleaned.get('publish_at')
        expires = cleaned.get('expires_at')
        if publish and expires and expires <= publish:
            raise ValidationError({'expires_at': 'Expiry must be after publish date.'})
        return cleaned