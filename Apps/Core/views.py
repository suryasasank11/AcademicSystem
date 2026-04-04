"""
core/views.py

Views: Role-aware dashboard (admin / professor / student),
       Global search, Notifications, System stats.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.http import JsonResponse

from apps.accounts.models import User, UserRole, StudentProfile, ProfessorProfile
from apps.courses.models import Course, Enrollment, Announcement
from apps.grades.models import Grade
from apps.attendance.models import AttendanceSession, AttendanceRecord
from apps.assignments.models import Assignment, AssignmentSubmission


# ---------------------------------------------------------------------------
# Dashboard dispatcher — routes to role-specific dashboard
# ---------------------------------------------------------------------------
@login_required
def dashboard_view(request):
    user = request.user
    if user.is_admin or user.is_superuser:
        return admin_dashboard(request)
    elif user.is_professor:
        return professor_dashboard(request)
    elif user.is_student:
        return student_dashboard(request)
    return render(request, 'core/dashboard_generic.html')


# ---------------------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------------------
def admin_dashboard(request):
    now = timezone.now()
    current_year = '2025-2026'
    current_semester = 'Spring'

    # System-wide stats
    stats = {
        'total_students': User.objects.filter(role=UserRole.STUDENT, is_active=True).count(),
        'total_professors': User.objects.filter(role=UserRole.PROFESSOR, is_active=True).count(),
        'total_courses': Course.objects.filter(is_active=True).count(),
        'total_enrollments': Enrollment.objects.filter(status='enrolled').count(),
        'active_courses': Course.objects.filter(
            status='active', academic_year=current_year, semester=current_semester
        ).count(),
        'pending_grades': Grade.objects.filter(is_finalized=False).count(),
        'pending_submissions': AssignmentSubmission.objects.filter(
            status='submitted', is_graded=False
        ).count(),
        'total_assignments': Assignment.objects.filter(status='published').count(),
    }

    # Recent enrollments
    recent_enrollments = Enrollment.objects.select_related(
        'student__user', 'course'
    ).order_by('-enrollment_date')[:8]

    # Recent users
    recent_users = User.objects.order_by('-date_joined')[:6]

    # Courses by enrollment fill rate
    courses_overview = Course.objects.filter(
        status='active'
    ).annotate(
        enrolled_count=Count('enrollments', filter=Q(enrollments__status='enrolled'))
    ).order_by('-enrolled_count')[:8]

    # Recent announcements
    announcements = Announcement.objects.select_related(
        'course', 'author'
    ).order_by('-publish_at')[:5]

    # Assignments due this week
    week_end = now + timezone.timedelta(days=7)
    upcoming_assignments = Assignment.objects.filter(
        due_date__gte=now,
        due_date__lte=week_end,
        status='published',
    ).select_related('course').order_by('due_date')[:5]

    return render(request, 'core/admin_dashboard.html', {
        'stats': stats,
        'recent_enrollments': recent_enrollments,
        'recent_users': recent_users,
        'courses_overview': courses_overview,
        'announcements': announcements,
        'upcoming_assignments': upcoming_assignments,
        'current_year': current_year,
        'current_semester': current_semester,
    })


# ---------------------------------------------------------------------------
# Professor Dashboard
# ---------------------------------------------------------------------------
def professor_dashboard(request):
    user = request.user
    now = timezone.now()

    try:
        professor_profile = user.professor_profile
    except ProfessorProfile.DoesNotExist:
        professor_profile = None

    # Professor's courses
    my_courses = Course.objects.filter(
        professor=user, is_active=True
    ).annotate(
        enrolled_count=Count('enrollments', filter=Q(enrollments__status='enrolled'))
    ).order_by('course_code')

    # Stats for this professor
    total_students = Enrollment.objects.filter(
        course__professor=user,
        course__is_active=True,
        status='enrolled'
    ).values('student').distinct().count()

    pending_grades = Grade.objects.filter(
        enrollment__course__professor=user,
        is_finalized=False,
        enrollment__status='enrolled',
    ).count()

    pending_submissions = AssignmentSubmission.objects.filter(
        assignment__course__professor=user,
        status__in=['submitted', 'late'],
        is_graded=False,
    ).count()

    stats = {
        'total_courses': my_courses.count(),
        'total_students': total_students,
        'pending_grades': pending_grades,
        'pending_submissions': pending_submissions,
    }

    # Recent submissions to grade
    recent_submissions = AssignmentSubmission.objects.filter(
        assignment__course__professor=user,
        status__in=['submitted', 'late'],
        is_graded=False,
    ).select_related(
        'assignment__course', 'student__user'
    ).order_by('-submitted_at')[:8]

    # Upcoming assignment deadlines
    week_end = now + timezone.timedelta(days=7)
    upcoming_assignments = Assignment.objects.filter(
        course__professor=user,
        due_date__gte=now,
        due_date__lte=week_end,
        status='published',
    ).select_related('course').order_by('due_date')[:5]

    # Recent attendance sessions
    recent_sessions = AttendanceSession.objects.filter(
        course__professor=user
    ).select_related('course').order_by('-date')[:5]

    # Course announcements
    recent_announcements = Announcement.objects.filter(
        course__professor=user
    ).order_by('-publish_at')[:5]

    return render(request, 'core/professor_dashboard.html', {
        'professor_profile': professor_profile,
        'stats': stats,
        'my_courses': my_courses,
        'recent_submissions': recent_submissions,
        'upcoming_assignments': upcoming_assignments,
        'recent_sessions': recent_sessions,
        'recent_announcements': recent_announcements,
    })


# ---------------------------------------------------------------------------
# Student Dashboard
# ---------------------------------------------------------------------------
def student_dashboard(request):
    user = request.user
    now = timezone.now()

    try:
        student_profile = user.student_profile
    except StudentProfile.DoesNotExist:
        student_profile = None
        return render(request, 'core/student_dashboard.html', {
            'student_profile': None,
            'error': 'Your student profile is not set up yet. Please contact the administrator.',
        })

    # Current enrollments
    enrollments = Enrollment.objects.filter(
        student=student_profile,
        status='enrolled',
    ).select_related(
        'course', 'course__professor'
    ).prefetch_related('grade').order_by('course__course_code')

    # Grades
    grades = Grade.objects.filter(
        enrollment__student=student_profile,
    ).select_related('enrollment__course').order_by('-graded_at')

    # GPA
    finalized_grades = grades.filter(is_finalized=True)
    gpa = 0.0
    if finalized_grades.exists():
        total = sum(float(g.grade_points) for g in finalized_grades)
        gpa = round(total / finalized_grades.count(), 2)

    # Upcoming assignments
    enrolled_course_ids = enrollments.values_list('course_id', flat=True)
    week_end = now + timezone.timedelta(days=7)
    upcoming_assignments = Assignment.objects.filter(
        course_id__in=enrolled_course_ids,
        due_date__gte=now,
        due_date__lte=week_end,
        status='published',
    ).select_related('course').order_by('due_date')

    # Overdue assignments (not submitted)
    submitted_ids = AssignmentSubmission.objects.filter(
        student=student_profile,
        status__in=['submitted', 'late', 'graded'],
    ).values_list('assignment_id', flat=True)

    overdue_assignments = Assignment.objects.filter(
        course_id__in=enrolled_course_ids,
        due_date__lt=now,
        status='published',
    ).exclude(id__in=submitted_ids).select_related('course').order_by('-due_date')[:5]

    # Recent announcements for enrolled courses
    recent_announcements = Announcement.objects.filter(
        course_id__in=enrolled_course_ids,
        publish_at__lte=now,
    ).select_related('course', 'author').order_by('-is_pinned', '-publish_at')[:6]

    # Attendance summary per course
    attendance_data = []
    for enrollment in enrollments:
        total_sessions = enrollment.attendance_records.count()
        present = enrollment.attendance_records.filter(
            status__in=['present', 'late', 'remote']
        ).count()
        pct = round((present / total_sessions * 100), 1) if total_sessions else 0
        attendance_data.append({
            'enrollment': enrollment,
            'total': total_sessions,
            'present': present,
            'percentage': pct,
        })

    stats = {
        'enrolled_courses': enrollments.count(),
        'gpa': gpa,
        'upcoming_assignments': upcoming_assignments.count(),
        'overdue_count': overdue_assignments.count(),
    }

    return render(request, 'core/student_dashboard.html', {
        'student_profile': student_profile,
        'stats': stats,
        'enrollments': enrollments,
        'grades': grades[:6],
        'upcoming_assignments': upcoming_assignments,
        'overdue_assignments': overdue_assignments,
        'recent_announcements': recent_announcements,
        'attendance_data': attendance_data,
    })


# ---------------------------------------------------------------------------
# Global Search
# ---------------------------------------------------------------------------
@login_required
def search_view(request):
    query = request.GET.get('q', '').strip()
    results = {}

    if query and len(query) >= 2:
        user = request.user

        if user.is_admin or user.is_superuser:
            results['users'] = User.objects.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query)
            )[:8]
            results['courses'] = Course.objects.filter(
                Q(course_code__icontains=query) | Q(title__icontains=query)
            )[:8]
            results['students'] = StudentProfile.objects.filter(
                Q(student_id__icontains=query) |
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query)
            ).select_related('user')[:8]

        elif user.is_professor:
            results['courses'] = Course.objects.filter(
                professor=user
            ).filter(
                Q(course_code__icontains=query) | Q(title__icontains=query)
            )[:8]
            results['students'] = StudentProfile.objects.filter(
                enrollments__course__professor=user
            ).filter(
                Q(student_id__icontains=query) |
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query)
            ).distinct().select_related('user')[:8]

        elif user.is_student:
            results['courses'] = Course.objects.filter(
                Q(course_code__icontains=query) | Q(title__icontains=query),
                is_active=True,
            )[:8]
            results['assignments'] = Assignment.objects.filter(
                course__enrollments__student__user=user,
                status='published',
            ).filter(
                Q(title__icontains=query)
            ).distinct()[:8]

    return render(request, 'core/search_results.html', {
        'query': query,
        'results': results,
    })


# ---------------------------------------------------------------------------
# System Info (Admin only)
# ---------------------------------------------------------------------------
@login_required
def system_stats_view(request):
    if not (request.user.is_admin or request.user.is_superuser):
        from django.shortcuts import redirect
        return redirect('core:dashboard')

    from apps.accounts.models import Department
    stats = {
        'users': {
            'total': User.objects.count(),
            'active': User.objects.filter(is_active=True).count(),
            'students': User.objects.filter(role=UserRole.STUDENT).count(),
            'professors': User.objects.filter(role=UserRole.PROFESSOR).count(),
            'admins': User.objects.filter(role=UserRole.ADMIN).count(),
        },
        'academic': {
            'departments': Department.objects.count(),
            'courses': Course.objects.count(),
            'active_courses': Course.objects.filter(status='active').count(),
            'enrollments': Enrollment.objects.count(),
            'active_enrollments': Enrollment.objects.filter(status='enrolled').count(),
        },
        'assessment': {
            'assignments': Assignment.objects.count(),
            'submissions': AssignmentSubmission.objects.count(),
            'graded_submissions': AssignmentSubmission.objects.filter(is_graded=True).count(),
            'grades': Grade.objects.count(),
            'finalized_grades': Grade.objects.filter(is_finalized=True).count(),
        },
        'attendance': {
            'sessions': AttendanceSession.objects.count(),
            'records': AttendanceRecord.objects.count(),
            'present_records': AttendanceRecord.objects.filter(status='present').count(),
        },
    }

    return render(request, 'core/system_stats.html', {'stats': stats})