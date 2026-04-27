"""
grades/forms.py

Forms: GradeForm, GradeComponentForm, BulkGradeForm
"""

from django import forms
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory

from .models import Grade, GradeComponent
from apps.courses.models import Enrollment


def _fc(placeholder=''):
    return {'class': 'form-control', 'placeholder': placeholder}


def _fs():
    return {'class': 'form-select'}


# ---------------------------------------------------------------------------
# Grade Form (professor enters grade for one student)
# ---------------------------------------------------------------------------
class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = [
            'numeric_score',
            'letter_grade',
            'midterm_score',
            'final_score',
            'assignment_score',
            'quiz_score',
            'project_score',
            'participation_score',
            'remarks',
            'is_finalized',
        ]
        widgets = {
            'numeric_score': forms.NumberInput(attrs={
                **_fc('0 – 100'), 'min': 0, 'max': 100, 'step': '0.01'
            }),
            'letter_grade': forms.Select(attrs=_fs(), choices=[('', '— Auto-compute —')] + Grade.LETTER_GRADE_CHOICES),
            'midterm_score': forms.NumberInput(attrs={**_fc('Midterm'), 'step': '0.01'}),
            'final_score': forms.NumberInput(attrs={**_fc('Final exam'), 'step': '0.01'}),
            'assignment_score': forms.NumberInput(attrs={**_fc('Assignments avg'), 'step': '0.01'}),
            'quiz_score': forms.NumberInput(attrs={**_fc('Quizzes avg'), 'step': '0.01'}),
            'project_score': forms.NumberInput(attrs={**_fc('Project'), 'step': '0.01'}),
            'participation_score': forms.NumberInput(attrs={**_fc('Participation'), 'step': '0.01'}),
            'remarks': forms.Textarea(attrs={**_fc('Feedback for student...'), 'rows': 3}),
            'is_finalized': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'numeric_score': 'Overall Numeric Score (%)',
            'is_finalized': 'Finalize Grade (cannot be changed without admin override)',
        }

    def clean_numeric_score(self):
        score = self.cleaned_data.get('numeric_score')
        if score is not None and (score < 0 or score > 100):
            raise ValidationError('Score must be between 0 and 100.')
        return score

    def clean(self):
        cleaned = super().clean()
        numeric = cleaned.get('numeric_score')
        letter = cleaned.get('letter_grade')
        # Must supply at least one
        if numeric is None and not letter:
            raise ValidationError(
                'Provide either a numeric score or a letter grade.'
            )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Auto-compute letter grade from numeric if letter not manually set
        if instance.numeric_score is not None and not instance.letter_grade:
            instance.compute_grade()
        elif instance.letter_grade:
            instance.grade_points = Grade.GPA_POINTS.get(instance.letter_grade, 0.00)
        if commit:
            instance.save()
        return instance


# ---------------------------------------------------------------------------
# Bulk Grade Form (grade multiple students at once)
# ---------------------------------------------------------------------------
class BulkGradeEntryForm(forms.Form):
    """Dynamic form for entering grades for all students in a course."""

    def __init__(self, *args, **kwargs):
        enrollments = kwargs.pop('enrollments', [])
        super().__init__(*args, **kwargs)

        for enrollment in enrollments:
            prefix = f'enrollment_{enrollment.pk}'
            field_score = forms.DecimalField(
                required=False,
                min_value=0,
                max_value=100,
                decimal_places=2,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': '0 – 100',
                    'step': '0.01',
                }),
                label=enrollment.student.user.get_full_name()
            )
            field_letter = forms.ChoiceField(
                required=False,
                choices=[('', '—')] + Grade.LETTER_GRADE_CHOICES,
                widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
                label='Letter'
            )
            field_remarks = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'Remarks...'
                }),
                label='Remarks'
            )
            self.fields[f'{prefix}_score'] = field_score
            self.fields[f'{prefix}_letter'] = field_letter
            self.fields[f'{prefix}_remarks'] = field_remarks

    def get_grade_data(self, enrollment):
        prefix = f'enrollment_{enrollment.pk}'
        return {
            'numeric_score': self.cleaned_data.get(f'{prefix}_score'),
            'letter_grade': self.cleaned_data.get(f'{prefix}_letter', ''),
            'remarks': self.cleaned_data.get(f'{prefix}_remarks', ''),
        }


# ---------------------------------------------------------------------------
# Grade Component Form
# ---------------------------------------------------------------------------
class GradeComponentForm(forms.ModelForm):
    class Meta:
        model = GradeComponent
        fields = ['name', 'component_type', 'weight', 'max_score', 'order']
        widgets = {
            'name': forms.TextInput(attrs=_fc('e.g. Midterm Exam')),
            'component_type': forms.Select(attrs=_fs()),
            'weight': forms.NumberInput(attrs={**_fc('e.g. 30'), 'min': 0, 'max': 100, 'step': '0.01'}),
            'max_score': forms.NumberInput(attrs={**_fc('e.g. 100'), 'min': 0, 'step': '0.01'}),
            'order': forms.NumberInput(attrs={**_fc('Display order'), 'min': 0}),
        }

    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight is not None and (weight < 0 or weight > 100):
            raise ValidationError('Weight must be between 0 and 100.')
        return weight


# Formset for managing multiple components at once
GradeComponentFormSet = modelformset_factory(
    GradeComponent,
    form=GradeComponentForm,
    extra=1,
    can_delete=True,
)