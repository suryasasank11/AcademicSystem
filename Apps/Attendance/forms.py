"""
attendance/forms.py

Forms: AttendanceSessionForm, AttendanceRecordForm, BulkAttendanceForm
"""

from django import forms
from django.forms import modelformset_factory

from .models import AttendanceSession, AttendanceRecord
from apps.courses.models import Course, Enrollment


def _fc(placeholder=''):
    return {'class': 'form-control', 'placeholder': placeholder}


def _fs():
    return {'class': 'form-select'}


# ---------------------------------------------------------------------------
# Attendance Session Form
# ---------------------------------------------------------------------------
class AttendanceSessionForm(forms.ModelForm):
    class Meta:
        model = AttendanceSession
        fields = ['course', 'date', 'session_type', 'topic', 'notes']
        widgets = {
            'course': forms.Select(attrs=_fs()),
            'date': forms.DateInput(attrs={**_fc(), 'type': 'date'}),
            'session_type': forms.Select(attrs=_fs()),
            'topic': forms.TextInput(attrs=_fc('Topic covered in this session')),
            'notes': forms.Textarea(attrs={**_fc('Additional notes...'), 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        professor = kwargs.pop('professor', None)
        super().__init__(*args, **kwargs)
        if professor:
            self.fields['course'].queryset = Course.objects.filter(
                professor=professor,
                is_active=True
            ).order_by('course_code')
        self.fields['course'].label_from_instance = (
            lambda c: f'{c.course_code} — {c.title}'
        )

    def clean(self):
        cleaned = super().clean()
        course = cleaned.get('course')
        date = cleaned.get('date')
        session_type = cleaned.get('session_type')
        if course and date and session_type:
            qs = AttendanceSession.objects.filter(
                course=course, date=date, session_type=session_type
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    'An attendance session of this type already exists for this course on this date.'
                )
        return cleaned


# ---------------------------------------------------------------------------
# Attendance Record Form (single student)
# ---------------------------------------------------------------------------
class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ['status', 'arrival_time', 'excuse_reason', 'notes']
        widgets = {
            'status': forms.Select(attrs=_fs()),
            'arrival_time': forms.TimeInput(attrs={**_fc(), 'type': 'time'}),
            'excuse_reason': forms.TextInput(attrs=_fc('Reason for excused absence')),
            'notes': forms.TextInput(attrs=_fc('Additional notes')),
        }


# ---------------------------------------------------------------------------
# Bulk Attendance Form (all students in a session at once)
# ---------------------------------------------------------------------------
class BulkAttendanceForm(forms.Form):
    """
    Dynamically builds fields for every enrolled student in a session.
    Field naming: record_{enrollment_pk}_status, record_{enrollment_pk}_notes
    """

    STATUS_CHOICES = AttendanceRecord.STATUS_CHOICES

    def __init__(self, *args, **kwargs):
        session = kwargs.pop('session', None)
        enrollments = kwargs.pop('enrollments', [])
        super().__init__(*args, **kwargs)

        self.enrollments = enrollments
        self.session = session

        for enrollment in enrollments:
            prefix = f'record_{enrollment.pk}'

            # Try to get existing record
            existing = AttendanceRecord.objects.filter(
                session=session, enrollment=enrollment
            ).first() if session else None

            self.fields[f'{prefix}_status'] = forms.ChoiceField(
                choices=self.STATUS_CHOICES,
                initial=existing.status if existing else 'present',
                widget=forms.Select(attrs={'class': 'form-select form-select-sm attendance-status-select'}),
                label='Status'
            )
            self.fields[f'{prefix}_excuse_reason'] = forms.CharField(
                required=False,
                initial=existing.excuse_reason if existing else '',
                widget=forms.TextInput(attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'Excuse reason (if applicable)',
                }),
                label='Excuse'
            )
            self.fields[f'{prefix}_notes'] = forms.CharField(
                required=False,
                initial=existing.notes if existing else '',
                widget=forms.TextInput(attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'Notes...',
                }),
                label='Notes'
            )

    def get_record_data(self, enrollment):
        prefix = f'record_{enrollment.pk}'
        return {
            'status': self.cleaned_data.get(f'{prefix}_status', 'absent'),
            'excuse_reason': self.cleaned_data.get(f'{prefix}_excuse_reason', ''),
            'notes': self.cleaned_data.get(f'{prefix}_notes', ''),
        }

    def iter_enrollments_with_fields(self):
        """Yield (enrollment, status_field, excuse_field, notes_field) tuples."""
        for enrollment in self.enrollments:
            prefix = f'record_{enrollment.pk}'
            yield (
                enrollment,
                self[f'{prefix}_status'],
                self[f'{prefix}_excuse_reason'],
                self[f'{prefix}_notes'],
            )