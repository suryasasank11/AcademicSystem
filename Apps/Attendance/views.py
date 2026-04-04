"""
attendance/views.py

Views: Session List/Create/Detail, Bulk Attendance Marking,
       Student Attendance Report, Attendance Summary.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Q
from django.utils import timezone

from .models import AttendanceSession, AttendanceRecord, AttendanceSummary
from .forms import AttendanceSessionForm, BulkAttendanceForm, AttendanceRecordForm
from apps.courses.models import Course, Enrollment
from apps.accounts.models import StudentProfile
from apps.accounts.mixins import (
    ProfessorRequiredMixin, ProfessorOrAdminMixin,
    AdminRequiredMixin, RoleContextMixin,
)
from apps.accounts.decorators import professor_required, login_required


# ---------------------------------------------------------------------------
# Session List
# ---------------------------------------------------------------------------
class AttendanceSessionListView(ProfessorOrAdminMixin, RoleContextMixin, ListView):
    model = AttendanceSession
    template_name = 'attendance/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = AttendanceSession.objects.select_related('course', 'created_by')

        if user.is_professor:
            qs = qs.filter(course__professor=user)

        course_id = self.request.GET.get('course', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')

        if course_id:
            qs = qs.filter(course_id=course_id)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        return qs.order_by('-date')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_professor:
            ctx['courses'] = Course.objects.filter(professor=user, is_active=True)
        else:
            ctx['courses'] = Course.objects.filter(is_active=True)
        ctx['filter_course'] = self.request.GET.get('course', '')
        ctx['filter_date_from'] = self.request.GET.get('date_from', '')
        ctx['filter_date_to'] = self.request.GET.get('date_to', '')
        return ctx


# ---------------------------------------------------------------------------
# Session Create
# ---------------------------------------------------------------------------
class AttendanceSessionCreateView(ProfessorOrAdminMixin, RoleContextMixin, CreateView):
    model = AttendanceSession
    form_class = AttendanceSessionForm
    template_name = 'attendance/session_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['professor'] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        course_pk = self.kwargs.get('course_pk')
        if course_pk:
            initial['course'] = course_pk
        initial['date'] = timezone.now().date()
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action'] = 'Create'
        return ctx

    def form_valid(self, form):
        session = form.save(commit=False)
        session.created_by = self.request.user
        session.save()

        # Auto-create absent records for all enrolled students
        session.create_records_for_enrolled_students()

        messages.success(
            self.request,
            f'Session created for {session.course.course_code} on {session.date}. '
            f'Attendance records initialized for {session.total_students} student(s).'
        )
        return redirect('attendance:mark', session_pk=session.pk)


# ---------------------------------------------------------------------------
# Session Detail
# ---------------------------------------------------------------------------
class AttendanceSessionDetailView(LoginRequiredMixin, RoleContextMixin, DetailView):
    model = AttendanceSession
    template_name = 'attendance/session_detail.html'
    context_object_name = 'session'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        session = self.get_object()
        ctx['records'] = session.records.select_related(
            'enrollment__student__user'
        ).order_by('enrollment__student__student_id')
        return ctx


# ---------------------------------------------------------------------------
# Bulk Attendance Marking
# ---------------------------------------------------------------------------
@professor_required
def mark_attendance_view(request, session_pk):
    """Mark attendance for all students in a session at once."""
    session = get_object_or_404(
        AttendanceSession.objects.select_related('course', 'created_by'),
        pk=session_pk
    )
    user = request.user

    if user.is_professor and session.course.professor != user:
        messages.error(request, 'You can only mark attendance for your own courses.')
        return redirect('attendance:session_list')

    if session.is_locked:
        messages.warning(request, 'This session is locked. Contact admin to unlock.')
        return redirect('attendance:session_detail', pk=session_pk)

    # Get all enrolled students for this course
    enrollments = Enrollment.objects.filter(
        course=session.course,
        status='enrolled'
    ).select_related('student__user').order_by('student__student_id')

    form = BulkAttendanceForm(
        request.POST or None,
        session=session,
        enrollments=list(enrollments)
    )

    if request.method == 'POST' and form.is_valid():
        saved = 0
        for enrollment in enrollments:
            data = form.get_record_data(enrollment)
            record, created = AttendanceRecord.objects.get_or_create(
                session=session,
                enrollment=enrollment,
            )
            record.status = data['status']
            record.excuse_reason = data['excuse_reason']
            record.notes = data['notes']
            record.marked_by = user
            record.save()

            # Update attendance summary
            summary, _ = AttendanceSummary.objects.get_or_create(enrollment=enrollment)
            summary.refresh()
            saved += 1

        messages.success(
            request,
            f'Attendance marked for {saved} student(s) in {session.course.course_code}.'
        )
        return redirect('attendance:session_detail', pk=session.pk)

    # Build (enrollment, existing_record) pairs for template
    record_map = {
        r.enrollment_id: r
        for r in AttendanceRecord.objects.filter(session=session)
    }

    return render(request, 'attendance/mark_attendance.html', {
        'session': session,
        'form': form,
        'enrollments': enrollments,
        'record_map': record_map,
    })


# ---------------------------------------------------------------------------
# Single Record Update
# ---------------------------------------------------------------------------
@professor_required
def update_attendance_record_view(request, pk):
    """Update a single student's attendance record."""
    record = get_object_or_404(
        AttendanceRecord.objects.select_related(
            'session__course', 'enrollment__student__user'
        ),
        pk=pk
    )
    user = request.user

    if user.is_professor and record.session.course.professor != user:
        messages.error(request, 'Permission denied.')
        return redirect('attendance:session_list')

    if record.session.is_locked and not (user.is_admin or user.is_superuser):
        messages.error(request, 'This session is locked.')
        return redirect('attendance:session_detail', pk=record.session.pk)

    form = AttendanceRecordForm(request.POST or None, instance=record)
    if request.method == 'POST' and form.is_valid():
        rec = form.save(commit=False)
        rec.marked_by = user
        rec.save()

        # Refresh summary
        summary, _ = AttendanceSummary.objects.get_or_create(enrollment=record.enrollment)
        summary.refresh()

        messages.success(request, 'Attendance record updated.')
        return redirect('attendance:session_detail', pk=record.session.pk)

    return render(request, 'attendance/update_record.html', {
        'form': form,
        'record': record,
    })


# ---------------------------------------------------------------------------
# Student Attendance Report (student views own attendance)
# ---------------------------------------------------------------------------
@login_required
def student_attendance_report_view(request):
    """Student's personal attendance report across all courses."""
    if not request.user.is_student:
        messages.error(request, 'Students only.')
        return redirect('core:dashboard')

    try:
        student = request.user.student_profile
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('core:dashboard')

    enrollments = Enrollment.objects.filter(
        student=student,
        status='enrolled'
    ).select_related('course')

    attendance_data = []
    for enrollment in enrollments:
        records = AttendanceRecord.objects.filter(
            enrollment=enrollment
        ).select_related('session').order_by('-session__date')

        total = records.count()
        present = records.filter(status__in=['present', 'late', 'remote']).count()
        absent = records.filter(status='absent').count()
        excused = records.filter(status='excused').count()
        pct = round((present / total * 100), 1) if total else 0

        attendance_data.append({
            'enrollment': enrollment,
            'records': records[:10],
            'total': total,
            'present': present,
            'absent': absent,
            'excused': excused,
            'percentage': pct,
            'status': (
                'danger' if pct < 75
                else 'warning' if pct < 85
                else 'success'
            ),
        })

    return render(request, 'attendance/student_report.html', {
        'student': student,
        'attendance_data': attendance_data,
    })


# ---------------------------------------------------------------------------
# Course Attendance Summary (professor view)
# ---------------------------------------------------------------------------
@professor_required
def course_attendance_summary_view(request, course_pk):
    """Attendance summary for all students in a course."""
    course = get_object_or_404(Course, pk=course_pk)
    user = request.user

    if user.is_professor and course.professor != user:
        messages.error(request, 'Permission denied.')
        return redirect('courses:list')

    sessions = AttendanceSession.objects.filter(
        course=course
    ).order_by('-date')

    enrollments = Enrollment.objects.filter(
        course=course, status='enrolled'
    ).select_related('student__user')

    # Build matrix: student → {session_date: status}
    matrix = []
    session_list = list(sessions)

    for enrollment in enrollments:
        records = {
            r.session_id: r
            for r in AttendanceRecord.objects.filter(enrollment=enrollment)
        }
        row = {
            'enrollment': enrollment,
            'records': [records.get(s.pk) for s in session_list],
        }
        total = len(session_list)
        present = sum(
            1 for r in records.values()
            if r and r.status in ('present', 'late', 'remote')
        )
        row['percentage'] = round((present / total * 100), 1) if total else 0
        row['present_count'] = present
        matrix.append(row)

    return render(request, 'attendance/course_summary.html', {
        'course': course,
        'sessions': session_list,
        'matrix': matrix,
        'total_sessions': len(session_list),
    })


# ---------------------------------------------------------------------------
# Lock / Unlock Session (Admin)
# ---------------------------------------------------------------------------
@login_required
def toggle_session_lock_view(request, pk):
    if not (request.user.is_admin or request.user.is_superuser):
        messages.error(request, 'Admin access required.')
        return redirect('core:dashboard')

    session = get_object_or_404(AttendanceSession, pk=pk)
    if request.method == 'POST':
        session.is_locked = not session.is_locked
        session.save(update_fields=['is_locked'])
        state = 'locked' if session.is_locked else 'unlocked'
        messages.success(request, f'Session {state} successfully.')
    return redirect('attendance:session_detail', pk=pk)