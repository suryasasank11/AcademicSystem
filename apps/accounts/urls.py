"""
accounts/urls.py

URL patterns for: Authentication, Profile, User Management (admin),
                  Department Management (admin).
Namespace: accounts
"""

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    path('login/',    views.login_view,    name='login'),
    path('logout/',   views.logout_view,   name='logout'),
    path('register/', views.register_view, name='register'),

    # ------------------------------------------------------------------
    # Profile (any logged-in user)
    # ------------------------------------------------------------------
    path('profile/',          views.profile_view,      name='profile'),
    path('profile/edit/',     views.profile_edit_view, name='profile_edit'),
    path('profile/password/', views.change_password_view, name='change_password'),

    # ------------------------------------------------------------------
    # User Management (admin only)
    # ------------------------------------------------------------------
    path('users/',
         views.UserListView.as_view(),
         name='user_list'),

    path('users/create/',
         views.UserCreateView.as_view(),
         name='user_create'),

    path('users/<int:pk>/',
         views.UserDetailView.as_view(),
         name='user_detail'),

    path('users/<int:pk>/edit/',
         views.UserEditView.as_view(),
         name='user_edit'),

    path('users/<int:pk>/delete/',
         views.UserDeleteView.as_view(),
         name='user_delete'),

    # AJAX: toggle active status
    path('users/<int:pk>/toggle-active/',
         views.toggle_user_active,
         name='user_toggle_active'),

    # ------------------------------------------------------------------
    # Department Management (admin only)
    # ------------------------------------------------------------------
    path('departments/',
         views.DepartmentListView.as_view(),
         name='department_list'),

    path('departments/create/',
         views.DepartmentCreateView.as_view(),
         name='department_create'),

    path('departments/<int:pk>/edit/',
         views.DepartmentUpdateView.as_view(),
         name='department_edit'),

    path('departments/<int:pk>/delete/',
         views.DepartmentDeleteView.as_view(),
         name='department_delete'),

    # ------------------------------------------------------------------
    # Convenience redirect aliases (used in templates)
    # ------------------------------------------------------------------
    # Student detail shortcut → user detail
    path('students/<int:pk>/',
         views.UserDetailView.as_view(),
         name='student_detail'),

    # Professor detail shortcut → user detail
    path('professors/<int:pk>/',
         views.UserDetailView.as_view(),
         name='professor_detail'),
]