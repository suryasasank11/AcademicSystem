"""
assignments/urls.py

URL patterns for: Assignments (CRUD), Submissions, Grading,
                  Comments, Publish/Close toggle.
Namespace: assignments
"""

from django.urls import path
from . import views

app_name = 'assignments'

urlpatterns = [

    # ------------------------------------------------------------------
    # Assignment List
    # ------------------------------------------------------------------
    path('',
         views.AssignmentListView.as_view(),
         name='list'),

    # ------------------------------------------------------------------
    # Assignment Create
    # ------------------------------------------------------------------
    path('create/',
         views.AssignmentCreateView.as_view(),
         name='create'),

    # Create assignment pre-linked to a specific course
    path('create/<int:course_pk>/',
         views.AssignmentCreateView.as_view(),
         name='create_for_course'),

    # ------------------------------------------------------------------
    # Assignment Detail
    # ------------------------------------------------------------------
    path('<int:pk>/',
         views.AssignmentDetailView.as_view(),
         name='detail'),

    # ------------------------------------------------------------------
    # Assignment Edit
    # ------------------------------------------------------------------
    path('<int:pk>/edit/',
         views.AssignmentUpdateView.as_view(),
         name='edit'),

    # ------------------------------------------------------------------
    # Assignment Delete
    # ------------------------------------------------------------------
    path('<int:pk>/delete/',
         views.AssignmentDeleteView.as_view(),
         name='delete'),

    # ------------------------------------------------------------------
    # Publish / Close toggle (professor action)
    # ------------------------------------------------------------------
    path('<int:pk>/toggle-status/',
         views.toggle_assignment_status_view,
         name='toggle_status'),

    # ------------------------------------------------------------------
    # Student: Submit an assignment
    # ------------------------------------------------------------------
    path('<int:pk>/submit/',
         views.submit_assignment_view,
         name='submit'),

    # ------------------------------------------------------------------
    # All submissions for an assignment (professor view)
    # ------------------------------------------------------------------
    path('<int:pk>/submissions/',
         views.assignment_submissions_view,
         name='submissions'),

    # ------------------------------------------------------------------
    # Submission Detail
    # ------------------------------------------------------------------
    path('submissions/<int:pk>/',
         views.SubmissionDetailView.as_view(),
         name='submission_detail'),

    # ------------------------------------------------------------------
    # Professor: Grade a submission
    # ------------------------------------------------------------------
    path('submissions/<int:pk>/grade/',
         views.grade_submission_view,
         name='grade_submission'),

    # ------------------------------------------------------------------
    # Add comment to a submission
    # ------------------------------------------------------------------
    path('submissions/<int:submission_pk>/comment/',
         views.add_submission_comment_view,
         name='add_comment'),
]