"""
grades/urls.py

URL patterns for: Grade List, Grade Entry (single + bulk),
                  Course Grade Overview, Student Grade Report,
                  Grade Finalization, Grade Components, Admin Override.
Namespace: grades
"""

from django.urls import path
from . import views

app_name = 'grades'

urlpatterns = [

    # ------------------------------------------------------------------
    # Grade List (professor/admin)
    # ------------------------------------------------------------------
    path('',
         views.GradeListView.as_view(),
         name='list'),

    # ------------------------------------------------------------------
    # Grade Detail
    # ------------------------------------------------------------------
    path('<int:pk>/',
         views.GradeDetailView.as_view(),
         name='detail'),

    # ------------------------------------------------------------------
    # Grade Entry — single student
    # ------------------------------------------------------------------
    path('entry/<int:enrollment_pk>/',
         views.grade_entry_view,
         name='entry'),

    # ------------------------------------------------------------------
    # Bulk Grade Entry — all students in a course at once
    # ------------------------------------------------------------------
    path('bulk/<int:course_pk>/',
         views.bulk_grade_entry_view,
         name='bulk_entry'),

    # ------------------------------------------------------------------
    # Course Grade Overview
    # ------------------------------------------------------------------
    path('course/<int:course_pk>/',
         views.course_grades_view,
         name='course_grades'),

    # ------------------------------------------------------------------
    # Student Grade Report (student views own grades)
    # ------------------------------------------------------------------
    path('my-grades/',
         views.student_grade_report_view,
         name='student_report'),

    # ------------------------------------------------------------------
    # Finalize a grade
    # ------------------------------------------------------------------
    path('<int:pk>/finalize/',
         views.finalize_grade_view,
         name='finalize'),

    # ------------------------------------------------------------------
    # Grade Components — manage course grading breakdown
    # ------------------------------------------------------------------
    path('components/<int:course_pk>/',
         views.manage_grade_components_view,
         name='components'),

    # ------------------------------------------------------------------
    # Admin: Override a finalized grade
    # ------------------------------------------------------------------
    path('<int:pk>/override/',
         views.admin_grade_override_view,
         name='override'),
]