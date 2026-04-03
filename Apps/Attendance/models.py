"""
attendance/models.py

Models: AttendanceSession, AttendanceRecord
Two-level attendance system:
  - AttendanceSession: a class meeting on a given date
  - AttendanceRecord: each student's status for that session
"""

from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.conf import settings


# ---------------------------------------------------------------------------
# Attendance Session (one per class meeting)
# ---------------------------------------------------------------------------
class AttendanceSession(models.Model):
    """
    Represents a single class meeting / lecture session.
    The professor marks attendance for this session.
    """

    SESSION_TYPE = [
        ('lecture', 'Lecture'),
        ('lab', 'Lab'),
        ('tutorial', 'Tutorial'),
        ('exam', 'Exam'),
        ('other', 'Other'),
    ]

    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='attendance_sessions',
        verbose_name='Course'
    )
    date = models.DateField(verbose_name='Session Date')
    session_type = models.CharField(
        max_length=20,
        choices=SESSION_TYPE,
        default='lecture',
        verbose_name='Session Type'
    )
    topic = models.CharField(
        max_length=300,
        blank=True,
        verbose_name='Topic Covered',
        help_text='What was covered in this session?'
    )
    notes = models.TextField(blank=True, verbose_name='Session Notes')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_sessions',
        verbose_name='Created By'
    )
    is_locked = models.BooleanField(
        default=False,
        verbose_name='Locked',
        help_text='Lock prevents further edits to attendance records'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attendance_sessions'
        verbose_name = 'Attendance Session'
        verbose_name_plural = 'Attendance Sessions'
        ordering = ['-date']
        unique_together = [('course', 'date', 'session_type')]
        indexes = [
            models.Index(fields=['course', '-date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f'{self.course.course_code} — {self.date} ({self.get_session_type_display()})'

    def get_absolute_url(self):
        return reverse('attendance:session_detail', kwargs={'pk': self.pk})

    @property
    def present_count(self):
        return self.records.filter(status='present').count()

    @property
    def absent_count(self):
        return self.records.filter(status='absent').count()

    @property
    def late_count(self):
        return self.records.filter(status='late').count()

    @property
    def total_students(self):
        return self.records.count()

    @property
    def attendance_rate(self):
        total = self.total_students
        if total == 0:
            return 0
        return round((self.present_count / total) * 100, 1)

    def create_records_for_enrolled_students(self):
        """Auto-create AttendanceRecord for all currently enrolled students."""
        from apps.courses.models import Enrollment
        enrolled = Enrollment.objects.filter(
            course=self.course,
            status='enrolled'
        ).select_related('student')

        records = []
        for enrollment in enrolled:
            if not AttendanceRecord.objects.filter(
                session=self,
                enrollment=enrollment
            ).exists():
                records.append(AttendanceRecord(
                    session=self,
                    enrollment=enrollment,
                    status='absent'  # default to absent
                ))
        if records:
            AttendanceRecord.objects.bulk_create(records)


# ---------------------------------------------------------------------------
# Attendance Record (per student, per session)
# ---------------------------------------------------------------------------
class AttendanceRecord(models.Model):

    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused Absence'),
        ('remote', 'Attended Remotely'),
    ]

    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name='records',
        verbose_name='Session'
    )
    enrollment = models.ForeignKey(
        'courses.Enrollment',
        on_delete=models.CASCADE,
        related_name='attendance_records',
        verbose_name='Enrollment'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='absent',
        verbose_name='Status'
    )
    arrival_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Arrival Time',
        help_text='Only for late arrivals'
    )
    excuse_reason = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Excuse Reason'
    )
    notes = models.CharField(max_length=500, blank=True, verbose_name='Notes')
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendance',
        verbose_name='Marked By'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attendance_records'
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'
        unique_together = [('session', 'enrollment')]
        ordering = ['session', 'enrollment__student__student_id']
        indexes = [
            models.Index(fields=['session', 'status']),
            models.Index(fields=['enrollment']),
        ]

    def __str__(self):
        return (
            f'{self.enrollment.student.user.get_full_name()} | '
            f'{self.session.date} | '
            f'{self.get_status_display()}'
        )

    @property
    def status_badge_class(self):
        return {
            'present': 'success',
            'absent': 'danger',
            'late': 'warning',
            'excused': 'info',
            'remote': 'primary',
        }.get(self.status, 'secondary')

    @property
    def status_icon(self):
        return {
            'present': 'fa-check-circle',
            'absent': 'fa-times-circle',
            'late': 'fa-clock',
            'excused': 'fa-info-circle',
            'remote': 'fa-laptop',
        }.get(self.status, 'fa-question-circle')


# ---------------------------------------------------------------------------
# Student Attendance Summary (computed / cached view)
# ---------------------------------------------------------------------------
class AttendanceSummary(models.Model):
    """
    Cached attendance statistics per student per course.
    Updated whenever AttendanceRecord changes.
    """

    enrollment = models.OneToOneField(
        'courses.Enrollment',
        on_delete=models.CASCADE,
        related_name='attendance_summary',
        verbose_name='Enrollment'
    )
    total_sessions = models.PositiveIntegerField(default=0)
    present_count = models.PositiveIntegerField(default=0)
    absent_count = models.PositiveIntegerField(default=0)
    late_count = models.PositiveIntegerField(default=0)
    excused_count = models.PositiveIntegerField(default=0)
    remote_count = models.PositiveIntegerField(default=0)
    attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attendance_summaries'
        verbose_name = 'Attendance Summary'
        verbose_name_plural = 'Attendance Summaries'

    def __str__(self):
        return f'{self.enrollment} — {self.attendance_percentage}% present'

    def refresh(self):
        """Recompute all stats from attendance records."""
        records = AttendanceRecord.objects.filter(enrollment=self.enrollment)
        self.total_sessions = records.count()
        self.present_count = records.filter(status='present').count()
        self.absent_count = records.filter(status='absent').count()
        self.late_count = records.filter(status='late').count()
        self.excused_count = records.filter(status='excused').count()
        self.remote_count = records.filter(status='remote').count()

        effective_present = self.present_count + self.late_count + self.remote_count
        if self.total_sessions > 0:
            self.attendance_percentage = round(
                (effective_present / self.total_sessions) * 100, 2
            )
        else:
            self.attendance_percentage = 0.00
        self.save()