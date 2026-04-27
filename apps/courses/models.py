"""
courses/models.py

Models: Course, Enrollment, Announcement
Handles all course management, student enrollment, and course announcements.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.urls import reverse
from django.conf import settings


# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------
class Course(models.Model):

    SCHEDULE_DAYS = [
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
        ('Sat', 'Saturday'),
        ('Sun', 'Sunday'),
    ]

    DELIVERY_MODE = [
        ('in_person', 'In Person'),
        ('online', 'Online'),
        ('hybrid', 'Hybrid'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    # Identification
    course_code = models.CharField(max_length=20, unique=True, verbose_name='Course Code')
    title = models.CharField(max_length=300, verbose_name='Course Title')
    description = models.TextField(blank=True, verbose_name='Description')
    syllabus = models.FileField(
        upload_to='syllabi/',
        blank=True,
        null=True,
        verbose_name='Syllabus (PDF)'
    )

    # Relationships
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='taught_courses',
        limit_choices_to={'role': 'professor'},
        verbose_name='Professor'
    )
    department = models.ForeignKey(
        'accounts.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses',
        verbose_name='Department'
    )

    # Academic period
    academic_year = models.CharField(
        max_length=20,
        verbose_name='Academic Year',
        default='2025-2026'
    )
    semester = models.CharField(
        max_length=10,
        choices=[('Fall', 'Fall'), ('Spring', 'Spring'), ('Summer', 'Summer')],
        verbose_name='Semester'
    )

    # Credits & capacity
    credits = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        verbose_name='Credits'
    )
    max_students = models.PositiveSmallIntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        verbose_name='Max Students'
    )

    # Schedule
    schedule_days = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Schedule Days',
        help_text='e.g. Mon, Wed, Fri'
    )
    start_time = models.TimeField(null=True, blank=True, verbose_name='Start Time')
    end_time = models.TimeField(null=True, blank=True, verbose_name='End Time')
    room = models.CharField(max_length=100, blank=True, verbose_name='Room / Location')
    delivery_mode = models.CharField(
        max_length=20,
        choices=DELIVERY_MODE,
        default='in_person',
        verbose_name='Delivery Mode'
    )
    meeting_link = models.URLField(blank=True, verbose_name='Online Meeting Link')

    # Dates
    start_date = models.DateField(null=True, blank=True, verbose_name='Course Start Date')
    end_date = models.DateField(null=True, blank=True, verbose_name='Course End Date')

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='Status'
    )
    is_active = models.BooleanField(default=True, verbose_name='Is Active')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses'
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        ordering = ['academic_year', 'semester', 'course_code']
        indexes = [
            models.Index(fields=['course_code']),
            models.Index(fields=['professor']),
            models.Index(fields=['status']),
            models.Index(fields=['academic_year', 'semester']),
        ]
        unique_together = [('course_code', 'academic_year', 'semester')]

    def __str__(self):
        return f'{self.course_code} — {self.title} ({self.semester} {self.academic_year})'

    def get_absolute_url(self):
        return reverse('courses:detail', kwargs={'pk': self.pk})

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def enrolled_count(self):
        return self.enrollments.filter(status='enrolled').count()

    @property
    def available_seats(self):
        return max(0, self.max_students - self.enrolled_count)

    @property
    def is_full(self):
        return self.enrolled_count >= self.max_students

    @property
    def enrollment_percentage(self):
        if self.max_students == 0:
            return 0
        return round((self.enrolled_count / self.max_students) * 100)

    @property
    def schedule_display(self):
        parts = [self.schedule_days]
        if self.start_time and self.end_time:
            parts.append(f'{self.start_time.strftime("%I:%M %p")} – {self.end_time.strftime("%I:%M %p")}')
        return ' | '.join(filter(None, parts))


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------
class Enrollment(models.Model):

    STATUS_CHOICES = [
        ('enrolled', 'Enrolled'),
        ('dropped', 'Dropped'),
        ('completed', 'Completed'),
        ('waitlisted', 'Waitlisted'),
        ('withdrawn', 'Withdrawn'),
        ('failed', 'Failed'),
    ]

    student = models.ForeignKey(
        'accounts.StudentProfile',
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='Student'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='Course'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='enrolled',
        verbose_name='Enrollment Status'
    )
    enrollment_date = models.DateTimeField(default=timezone.now, verbose_name='Enrollment Date')
    drop_date = models.DateTimeField(null=True, blank=True, verbose_name='Drop Date')
    completion_date = models.DateTimeField(null=True, blank=True, verbose_name='Completion Date')
    notes = models.TextField(blank=True, verbose_name='Notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'enrollments'
        verbose_name = 'Enrollment'
        verbose_name_plural = 'Enrollments'
        unique_together = [('student', 'course')]
        ordering = ['-enrollment_date']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['course', 'status']),
        ]

    def __str__(self):
        return f'{self.student} → {self.course.course_code} [{self.status}]'

    def get_absolute_url(self):
        return reverse('courses:enrollment_detail', kwargs={'pk': self.pk})

    @property
    def final_grade(self):
        try:
            return self.grade
        except Exception:
            return None

    @property
    def attendance_percentage(self):
        total = self.attendance_records.count()
        if total == 0:
            return 0
        present = self.attendance_records.filter(status='present').count()
        return round((present / total) * 100, 1)


# ---------------------------------------------------------------------------
# Announcement
# ---------------------------------------------------------------------------
class Announcement(models.Model):

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    TYPE_CHOICES = [
        ('general', 'General'),
        ('assignment', 'Assignment'),
        ('exam', 'Exam'),
        ('grade', 'Grade Release'),
        ('schedule', 'Schedule Change'),
        ('other', 'Other'),
    ]

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='announcements',
        verbose_name='Course'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='announcements',
        verbose_name='Author'
    )
    title = models.CharField(max_length=300, verbose_name='Title')
    content = models.TextField(verbose_name='Content')
    announcement_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='general',
        verbose_name='Type'
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name='Priority'
    )
    is_pinned = models.BooleanField(default=False, verbose_name='Pinned')
    send_email = models.BooleanField(
        default=False,
        verbose_name='Send Email Notification',
        help_text='Notify enrolled students via email'
    )
    publish_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Publish At'
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Expires At'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'announcements'
        verbose_name = 'Announcement'
        verbose_name_plural = 'Announcements'
        ordering = ['-is_pinned', '-publish_at']
        indexes = [
            models.Index(fields=['course', '-publish_at']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        return f'[{self.course.course_code}] {self.title}'

    def get_absolute_url(self):
        return reverse('courses:announcement_detail', kwargs={'pk': self.pk})

    @property
    def is_active(self):
        now = timezone.now()
        if self.publish_at > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True

    @property
    def priority_badge_class(self):
        return {
            'low': 'secondary',
            'normal': 'primary',
            'high': 'warning',
            'urgent': 'danger',
        }.get(self.priority, 'secondary')