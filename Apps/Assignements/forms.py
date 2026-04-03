"""
assignments/forms.py

Forms: AssignmentForm, AssignmentSubmissionForm,
       GradeSubmissionForm, SubmissionCommentForm
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Assignment, AssignmentSubmission, SubmissionComment
from apps.courses.models import Course


def _fc(placeholder=''):
    return {'class': 'form-control', 'placeholder': placeholder}


def _fs():
    return {'class': 'form-select'}


# ---------------------------------------------------------------------------
# Assignment Form (Professor creates/edits an assignment)
# ---------------------------------------------------------------------------
class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = [
            'course', 'title', 'description', 'assignment_type',
            'status', 'max_score', 'weight',
            'assigned_date', 'due_date',
            'late_submission_allowed', 'late_penalty_percent',
            'attachment', 'reference_url',
            'allow_resubmission', 'max_submissions', 'submission_format',
        ]
        widgets = {
            'course': forms.Select(attrs=_fs()),
            'title': forms.TextInput(attrs=_fc('Assignment title')),
            'description': forms.Textarea(attrs={
                **_fc('Detailed instructions for students...'), 'rows': 6
            }),
            'assignment_type': forms.Select(attrs=_fs()),
            'status': forms.Select(attrs=_fs()),
            'max_score': forms.NumberInput(attrs={**_fc('100'), 'min': 1, 'step': '0.01'}),
            'weight': forms.NumberInput(attrs={
                **_fc('Weight in final grade (%)'), 'min': 0, 'max': 100, 'step': '0.01'
            }),
            'assigned_date': forms.DateTimeInput(attrs={**_fc(), 'type': 'datetime-local'}),
            'due_date': forms.DateTimeInput(attrs={**_fc(), 'type': 'datetime-local'}),
            'late_submission_allowed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'late_penalty_percent': forms.NumberInput(attrs={
                **_fc('e.g. 10'), 'min': 0, 'max': 100, 'step': '0.01'
            }),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
            'reference_url': forms.URLInput(attrs=_fc('https://')),
            'allow_resubmission': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_submissions': forms.NumberInput(attrs={**_fc('1'), 'min': 1}),
            'submission_format': forms.TextInput(attrs=_fc('PDF, DOCX, ZIP...')),
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
        due = cleaned.get('due_date')
        assigned = cleaned.get('assigned_date')
        if due and assigned and due <= assigned:
            raise ValidationError({'due_date': 'Due date must be after the assigned date.'})
        return cleaned


# ---------------------------------------------------------------------------
# Assignment Submission Form (Student submits work)
# ---------------------------------------------------------------------------
class AssignmentSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['submission_text', 'submission_file', 'submission_url']
        widgets = {
            'submission_text': forms.Textarea(attrs={
                **_fc('Type or paste your answer here...'), 'rows': 8
            }),
            'submission_file': forms.FileInput(attrs={'class': 'form-control'}),
            'submission_url': forms.URLInput(attrs=_fc('https://github.com/... or other URL')),
        }
        labels = {
            'submission_text': 'Written Response',
            'submission_file': 'Upload File',
            'submission_url': 'External URL (GitHub, Google Drive, etc.)',
        }

    def clean(self):
        cleaned = super().clean()
        text = cleaned.get('submission_text', '').strip()
        file = cleaned.get('submission_file')
        url = cleaned.get('submission_url', '').strip()
        if not text and not file and not url:
            raise ValidationError(
                'Please provide at least one of: written response, file upload, or URL.'
            )
        return cleaned


# ---------------------------------------------------------------------------
# Grade Submission Form (Professor grades a submission)
# ---------------------------------------------------------------------------
class GradeSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['score', 'feedback', 'is_graded']
        widgets = {
            'score': forms.NumberInput(attrs={
                **_fc('Score'), 'min': 0, 'step': '0.01'
            }),
            'feedback': forms.Textarea(attrs={
                **_fc('Detailed feedback for the student...'), 'rows': 5
            }),
            'is_graded': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_graded': 'Mark as Graded (visible to student)',
        }

    def __init__(self, *args, **kwargs):
        self.assignment = kwargs.pop('assignment', None)
        super().__init__(*args, **kwargs)
        if self.assignment:
            self.fields['score'].widget.attrs['max'] = float(self.assignment.max_score)
            self.fields['score'].help_text = f'Max score: {self.assignment.max_score}'

    def clean_score(self):
        score = self.cleaned_data.get('score')
        if score is not None and self.assignment:
            if score < 0:
                raise ValidationError('Score cannot be negative.')
            if score > self.assignment.max_score:
                raise ValidationError(
                    f'Score cannot exceed max score of {self.assignment.max_score}.'
                )
        return score


# ---------------------------------------------------------------------------
# Submission Comment Form
# ---------------------------------------------------------------------------
class SubmissionCommentForm(forms.ModelForm):
    class Meta:
        model = SubmissionComment
        fields = ['content', 'is_private']
        widgets = {
            'content': forms.Textarea(attrs={
                **_fc('Write a comment...'), 'rows': 3
            }),
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_private': 'Private (only visible to instructors)',
        }