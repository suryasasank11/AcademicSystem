"""
attendance/urls.py

URL patterns for: Attendance Sessions (CRUD), Bulk Marking,
                  Student Report, Course Summary, Lock/Unlock.
Namespace: attendance
"""

from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [

    # ------------------------------------------------------------------
    # Attendance Session List
    # ------------------------------------------------------------------
    path('',
         views.AttendanceSessionListView.as_view(),
         name='session_list'),

    # ------------------------------------------------------------------
    # Session Create
    # ------------------------------------------------------------------
    path('sessions/create/',
         views.AttendanceSessionCreateView.as_view(),
         name='session_create'),

    # Create session pre-linked to a specific course
    path('sessions/create/<int:course_pk>/',
         views.AttendanceSessionCreateView.as_view(),
         name='session_create_for_course'),

    # ------------------------------------------------------------------
    # Session Detail
    # ------------------------------------------------------------------
    path('sessions/<int:pk>/',
         views.AttendanceSessionDetailView.as_view(),
         name='session_detail'),

    # ------------------------------------------------------------------
    # Bulk Attendance Marking — mark all students in one session
    # ------------------------------------------------------------------
    path('sessions/<int:session_pk>/mark/',
         views.mark_attendance_view,
         name='mark'),

    # ------------------------------------------------------------------
    # Update a Single Attendance Record
    # ------------------------------------------------------------------
    path('records/<int:pk>/update/',
         views.update_attendance_record_view,
         name='update_record'),

    # ------------------------------------------------------------------
    # Student: My Attendance Report (across all enrolled courses)
    # ------------------------------------------------------------------
    path('my-attendance/',
         views.student_attendance_report_view,
         name='student_report'),

    # ------------------------------------------------------------------
    # Professor/Admin: Full attendance summary for a course
    # ------------------------------------------------------------------
    path('course/<int:course_pk>/summary/',
         views.course_attendance_summary_view,
         name='course_summary'),

    # ------------------------------------------------------------------
    # Admin: Lock / Unlock a session
    # ------------------------------------------------------------------
    path('sessions/<int:pk>/toggle-lock/',
         views.toggle_session_lock_view,
         name='toggle_lock'),
]