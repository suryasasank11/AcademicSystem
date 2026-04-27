"""
courses/urls.py

URL patterns for: Courses (CRUD), Enrollments, Announcements,
                  Self-enrollment, Drop course.
Namespace: courses
"""

from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [

    # ------------------------------------------------------------------
    # Courses — CRUD
    # ------------------------------------------------------------------
    path('',
         views.CourseListView.as_view(),
         name='list'),

    path('create/',
         views.CourseCreateView.as_view(),
         name='create'),

    path('<int:pk>/',
         views.CourseDetailView.as_view(),
         name='detail'),

    path('<int:pk>/edit/',
         views.CourseUpdateView.as_view(),
         name='edit'),

    path('<int:pk>/delete/',
         views.CourseDeleteView.as_view(),
         name='delete'),

    # ------------------------------------------------------------------
    # Enrollment — Admin/Professor actions
    # ------------------------------------------------------------------
    path('enrollments/',
         views.EnrollmentListView.as_view(),
         name='enrollment_list'),

    path('<int:course_pk>/enroll/',
         views.enroll_student_view,
         name='enroll_student'),

    path('enrollments/<int:pk>/drop/',
         views.drop_enrollment_view,
         name='drop_enrollment'),

    path('enrollments/<int:pk>/update-status/',
         views.update_enrollment_status_view,
         name='update_enrollment_status'),

    # ------------------------------------------------------------------
    # Enrollment — Student self-service
    # ------------------------------------------------------------------
    path('enroll/',
         views.self_enroll_view,
         name='self_enroll'),

    # ------------------------------------------------------------------
    # Announcements — CRUD
    # ------------------------------------------------------------------
    path('announcements/',
         views.AnnouncementListView.as_view(),
         name='announcement_list'),

    path('announcements/<int:pk>/',
         views.AnnouncementDetailView.as_view(),
         name='announcement_detail'),

    path('<int:course_pk>/announcements/create/',
         views.AnnouncementCreateView.as_view(),
         name='announcement_create'),

    path('announcements/<int:pk>/edit/',
         views.AnnouncementUpdateView.as_view(),
         name='announcement_edit'),

    path('announcements/<int:pk>/delete/',
         views.AnnouncementDeleteView.as_view(),
         name='announcement_delete'),
]