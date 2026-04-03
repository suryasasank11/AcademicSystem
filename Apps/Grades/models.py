"""
grades/models.py

Models: Grade, GradeComponent
Full grading system with weighted components, letter grade computation,
GPA point conversion, and grade history tracking.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.urls import reverse
from django.conf import settings


# ---------------------------------------------------------------------------
# Grade Component (Midterm, Final, Quiz, Project, etc.)
# ---------------------------------------------------------------------------
class GradeComponent(models.Model):
    """
    Defines the grading breakdown for a course.
    e.g. Midterm 30%, Final 40%, Assignments 20%, Participation 10%
    """

    COMPONENT_TYPE = [
        ('midterm', 'Midterm Exam'),
        ('final', 'Final Exam'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
        ('project', 'Project'),
        ('lab', 'Lab'),
        ('participation', 'Participation'),
        ('other', 'Other'),
    ]

    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='grade_components',
        verbose_name='Course'
    )
    name = models.CharField(max_length=200, verbose_name='Component Name')
    component_type = models.CharField(
        max_length=20,
        choices=COMPONENT_TYPE,
        default='other',
        verbose_name='Type'
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Weight (%)',
        help_text='Percentage weight toward final grade (all weights must sum to 100)'
    )
    max_score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=100.00,
        validators=[MinValueValidator(0)],
        verbose_name='Max Score'
    )
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Display Order')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'grade_components'
        verbose_name = 'Grade Component'
        verbose_name_plural = 'Grade Components'
        ordering = ['course', 'order', 'name']

    def __str__(self):
        return f'{self.course.course_code} — {self.name} ({self.weight}%)'


# ---------------------------------------------------------------------------
# Grade
# ---------------------------------------------------------------------------
class Grade(models.Model):
    """
    Final/overall grade for a student in a course enrollment.
    Stores raw score, computed letter grade, and GPA points.
    """

    LETTER_GRADE_CHOICES = [
        ('A+', 'A+'), ('A', 'A'), ('A-', 'A-'),
        ('B+', 'B+'), ('B', 'B'), ('B-', 'B-'),
        ('C+', 'C+'), ('C', 'C'), ('C-', 'C-'),
        ('D+', 'D+'), ('D', 'D'), ('D-', 'D-'),
        ('F', 'F'),
        ('W', 'W — Withdrawn'),
        ('I', 'I — Incomplete'),
        ('P', 'P — Pass'),
        ('NP', 'NP — No Pass'),
    ]

    # GPA conversion table (4.0 scale)
    GPA_POINTS = {
        'A+': 4.00, 'A': 4.00, 'A-': 3.70,
        'B+': 3.30, 'B': 3.00, 'B-': 2.70,
        'C+': 2.30, 'C': 2.00, 'C-': 1.70,
        'D+': 1.30, 'D': 1.00, 'D-': 0.70,
        'F': 0.00,
        'W': 0.00, 'I': 0.00, 'P': 0.00, 'NP': 0.00,
    }

    enrollment = models.OneToOneField(
        'courses.Enrollment',
        on_delete=models.CASCADE,
        related_name='grade',
        verbose_name='Enrollment'
    )
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='grades_given',
        limit_choices_to={'role': 'professor'},
        verbose_name='Graded By'
    )

    # Score
    numeric_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Numeric Score (%)'
    )
    letter_grade = models.CharField(
        max_length=3,
        choices=LETTER_GRADE_CHOICES,
        blank=True,
        verbose_name='Letter Grade'
    )
    grade_points = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.00,
        verbose_name='GPA Points'
    )

    # Component scores (JSON-like per component)
    midterm_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Midterm Score')
    final_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Final Exam Score')
    assignment_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Assignment Score')
    quiz_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Quiz Score')
    project_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Project Score')
    participation_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Participation Score')

    # Status & Remarks
    is_finalized = models.BooleanField(default=False, verbose_name='Finalized')
    remarks = models.TextField(blank=True, verbose_name='Professor Remarks')
    graded_at = models.DateTimeField(null=True, blank=True, verbose_name='Graded At')
    finalized_at = models.DateTimeField(null=True, blank=True, verbose_name='Finalized At')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'grades'
        verbose_name = 'Grade'
        verbose_name_plural = 'Grades'
        ordering = ['-graded_at']
        indexes = [
            models.Index(fields=['enrollment']),
            models.Index(fields=['letter_grade']),
            models.Index(fields=['is_finalized']),
        ]

    def __str__(self):
        return (
            f'{self.enrollment.student} | '
            f'{self.enrollment.course.course_code} | '
            f'{self.letter_grade or "No Grade"}'
        )

    def get_absolute_url(self):
        return reverse('grades:detail', kwargs={'pk': self.pk})

    # ------------------------------------------------------------------
    # Grade Computation
    # ------------------------------------------------------------------
    @staticmethod
    def score_to_letter(score):
        """Convert numeric percentage score to letter grade."""
        if score is None:
            return ''
        score = float(score)
        if score >= 97:   return 'A+'
        elif score >= 93: return 'A'
        elif score >= 90: return 'A-'
        elif score >= 87: return 'B+'
        elif score >= 83: return 'B'
        elif score >= 80: return 'B-'
        elif score >= 77: return 'C+'
        elif score >= 73: return 'C'
        elif score >= 70: return 'C-'
        elif score >= 67: return 'D+'
        elif score >= 63: return 'D'
        elif score >= 60: return 'D-'
        else:             return 'F'

    def compute_grade(self):
        """Auto-compute letter grade and GPA points from numeric score."""
        if self.numeric_score is not None:
            self.letter_grade = self.score_to_letter(self.numeric_score)
            self.grade_points = self.GPA_POINTS.get(self.letter_grade, 0.00)

    def finalize(self, graded_by=None):
        """Mark grade as finalized and record timestamps."""
        self.is_finalized = True
        self.finalized_at = timezone.now()
        if graded_by:
            self.graded_by = graded_by
        self.save()
        # Trigger student GPA recalculation
        self.enrollment.student.update_gpa()

    def save(self, *args, **kwargs):
        if self.numeric_score is not None and not self.letter_grade:
            self.compute_grade()
        if self.letter_grade and not self.grade_points:
            self.grade_points = self.GPA_POINTS.get(self.letter_grade, 0.00)
        if not self.graded_at and (self.numeric_score or self.letter_grade):
            self.graded_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def grade_badge_class(self):
        """Bootstrap badge color based on letter grade."""
        if not self.letter_grade:
            return 'secondary'
        if self.letter_grade.startswith('A'):
            return 'success'
        elif self.letter_grade.startswith('B'):
            return 'primary'
        elif self.letter_grade.startswith('C'):
            return 'warning'
        elif self.letter_grade.startswith('D'):
            return 'orange'
        elif self.letter_grade == 'F':
            return 'danger'
        return 'secondary'

    @property
    def is_passing(self):
        return self.letter_grade not in ('F', 'NP', '') and self.letter_grade is not None


# ---------------------------------------------------------------------------
# Grade History (Audit Trail)
# ---------------------------------------------------------------------------
class GradeHistory(models.Model):
    """Tracks every change made to a grade for auditing purposes."""

    grade = models.ForeignKey(
        Grade,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name='Grade'
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Changed By'
    )
    old_numeric_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    new_numeric_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    old_letter_grade = models.CharField(max_length=3, blank=True)
    new_letter_grade = models.CharField(max_length=3, blank=True)
    reason = models.TextField(blank=True, verbose_name='Reason for Change')
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'grade_history'
        verbose_name = 'Grade History'
        verbose_name_plural = 'Grade History'
        ordering = ['-changed_at']

    def __str__(self):
        return f'Grade #{self.grade_id} changed at {self.changed_at.strftime("%Y-%m-%d %H:%M")}'