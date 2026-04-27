"""
assignments/models.py

Models: Assignment, AssignmentSubmission, SubmissionComment
Full assignment lifecycle: creation → submission → grading → feedback.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.urls import reverse
from django.conf import settings


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------
class Assignment(models.Model):

    TYPE_CHOICES = [
        ('homework', 'Homework'),
        ('quiz', 'Quiz'),
        ('midterm', 'Midterm Exam'),
        ('final', 'Final Exam'),
        ('project', 'Project'),
        ('lab', 'Lab Report'),
        ('essay', 'Essay'),
        ('presentation', 'Presentation'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('closed', 'Closed'),
        ('graded', 'Graded'),
    ]

    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name='Course'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_assignments',
        limit_choices_to={'role': 'professor'},
        verbose_name='Created By'
    )
    title = models.CharField(max_length=300, verbose_name='Title')
    description = models.TextField(verbose_name='Description / Instructions')
    assignment_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='homework',
        verbose_name='Type'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Status'
    )

    # Grading
    max_score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=100.00,
        validators=[MinValueValidator(1)],
        verbose_name='Maximum Score'
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Weight in Final Grade (%)'
    )

    # Dates
    assigned_date = models.DateTimeField(default=timezone.now, verbose_name='Assigned Date')
    due_date = models.DateTimeField(verbose_name='Due Date')
    late_submission_allowed = models.BooleanField(
        default=False,
        verbose_name='Allow Late Submissions'
    )
    late_penalty_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Late Penalty (%)',
        help_text='Percentage deducted for late submissions'
    )

    # Attachments
    attachment = models.FileField(
        upload_to='assignments/files/',
        blank=True,
        null=True,
        verbose_name='Attachment'
    )
    reference_url = models.URLField(blank=True, verbose_name='Reference URL')

    # Settings
    allow_resubmission = models.BooleanField(default=False, verbose_name='Allow Resubmission')
    max_submissions = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='Max Submissions Allowed'
    )
    submission_format = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Accepted File Formats',
        help_text='e.g. PDF, DOCX, ZIP'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignments'
        verbose_name = 'Assignment'
        verbose_name_plural = 'Assignments'
        ordering = ['due_date', 'course']
        indexes = [
            models.Index(fields=['course', 'status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f'[{self.course.course_code}] {self.title}'

    def get_absolute_url(self):
        return reverse('assignments:detail', kwargs={'pk': self.pk})

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def is_overdue(self):
        return timezone.now() > self.due_date and self.status != 'closed'

    @property
    def is_published(self):
        return self.status == 'published'

    @property
    def days_until_due(self):
        delta = self.due_date - timezone.now()
        return delta.days

    @property
    def submission_count(self):
        return self.submissions.count()

    @property
    def graded_count(self):
        return self.submissions.filter(is_graded=True).count()

    @property
    def pending_grading_count(self):
        return self.submissions.filter(
            is_graded=False,
            status='submitted'
        ).count()

    @property
    def due_date_badge_class(self):
        if self.is_overdue:
            return 'danger'
        elif self.days_until_due <= 3:
            return 'warning'
        return 'success'

    def get_student_submission(self, student_profile):
        """Return this student's latest submission for this assignment."""
        return self.submissions.filter(
            student=student_profile
        ).order_by('-submitted_at').first()


# ---------------------------------------------------------------------------
# Assignment Submission
# ---------------------------------------------------------------------------
class AssignmentSubmission(models.Model):

    STATUS_CHOICES = [
        ('draft', 'Saved as Draft'),
        ('submitted', 'Submitted'),
        ('late', 'Submitted Late'),
        ('resubmitted', 'Resubmitted'),
        ('graded', 'Graded'),
        ('returned', 'Returned for Revision'),
    ]

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name='Assignment'
    )
    student = models.ForeignKey(
        'accounts.StudentProfile',
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name='Student'
    )

    # Submission content
    submission_text = models.TextField(
        blank=True,
        verbose_name='Submission Text',
        help_text='Written response / answer'
    )
    submission_file = models.FileField(
        upload_to='submissions/files/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Submitted File'
    )
    submission_url = models.URLField(blank=True, verbose_name='Submission URL (e.g. GitHub)')
    submission_number = models.PositiveSmallIntegerField(
        default=1,
        verbose_name='Submission Number'
    )

    # Status & timing
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Status'
    )
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='Submitted At')
    is_late = models.BooleanField(default=False, verbose_name='Late Submission')

    # Grading
    score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name='Score'
    )
    adjusted_score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Adjusted Score (after penalties)'
    )
    is_graded = models.BooleanField(default=False, verbose_name='Graded')
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_submissions',
        verbose_name='Graded By'
    )
    graded_at = models.DateTimeField(null=True, blank=True, verbose_name='Graded At')
    feedback = models.TextField(blank=True, verbose_name='Instructor Feedback')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignment_submissions'
        verbose_name = 'Assignment Submission'
        verbose_name_plural = 'Assignment Submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['assignment', 'student']),
            models.Index(fields=['is_graded']),
            models.Index(fields=['submitted_at']),
        ]

    def __str__(self):
        return (
            f'{self.student.user.get_full_name()} → '
            f'{self.assignment.title} '
            f'[{self.get_status_display()}]'
        )

    def save(self, *args, **kwargs):
        # Auto-mark as late
        if self.submitted_at and self.submitted_at > self.assignment.due_date:
            self.is_late = True
            if self.status == 'submitted':
                self.status = 'late'

        # Apply late penalty
        if self.score is not None and self.is_late and self.assignment.late_penalty_percent:
            penalty = float(self.score) * (float(self.assignment.late_penalty_percent) / 100)
            self.adjusted_score = round(float(self.score) - penalty, 2)
        else:
            self.adjusted_score = self.score

        # Mark graded timestamp
        if self.is_graded and not self.graded_at:
            self.graded_at = timezone.now()
            self.status = 'graded'

        super().save(*args, **kwargs)

    def submit(self):
        """Mark as submitted with current timestamp."""
        self.submitted_at = timezone.now()
        self.status = 'submitted'
        self.save()

    @property
    def score_percentage(self):
        if self.score is None:
            return None
        return round((float(self.adjusted_score or self.score) / float(self.assignment.max_score)) * 100, 1)

    @property
    def status_badge_class(self):
        return {
            'draft': 'secondary',
            'submitted': 'primary',
            'late': 'warning',
            'resubmitted': 'info',
            'graded': 'success',
            'returned': 'danger',
        }.get(self.status, 'secondary')


# ---------------------------------------------------------------------------
# Submission Comment (threaded feedback)
# ---------------------------------------------------------------------------
class SubmissionComment(models.Model):
    """
    Comments/feedback thread on a submission.
    Both professor and student can add comments.
    """

    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Submission'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submission_comments',
        verbose_name='Author'
    )
    content = models.TextField(verbose_name='Comment')
    is_private = models.BooleanField(
        default=False,
        verbose_name='Private',
        help_text='Private comments are only visible to professors'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='Reply To'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'submission_comments'
        verbose_name = 'Submission Comment'
        verbose_name_plural = 'Submission Comments'
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author.get_full_name()} on {self.submission}'