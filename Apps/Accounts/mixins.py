"""
accounts/mixins.py

Class-based view mixins for role-based access control.
Use these with Django's CBVs (ListView, DetailView, CreateView, etc.)

Usage:
    class MyCourseView(ProfessorRequiredMixin, ListView):
        model = Course
"""

from django.contrib.auth.mixins import LoginRequiredMixin, AccessMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied


# ---------------------------------------------------------------------------
# Base Role Mixin
# ---------------------------------------------------------------------------
class RoleRequiredMixin(LoginRequiredMixin, AccessMixin):
    """
    Base mixin. Subclass and override `allowed_roles` list
    or override `check_role(user)`.
    """
    allowed_roles = []          # e.g. ['admin', 'professor']
    permission_denied_message = 'You do not have permission to access this page.'
    redirect_url = None         # falls back to LOGIN_REDIRECT_URL if None

    def check_role(self, user):
        """Return True if the user is allowed. Override for custom logic."""
        if user.is_superuser:
            return True
        return user.role in self.allowed_roles

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, self.permission_denied_message)
            return redirect(self.redirect_url or 'core:dashboard')
        return super().handle_no_permission()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self.check_role(request.user):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Concrete Role Mixins
# ---------------------------------------------------------------------------
class AdminRequiredMixin(RoleRequiredMixin):
    """Only admin (or superuser) can access."""
    allowed_roles = ['admin']
    permission_denied_message = 'Administrator access required.'


class ProfessorRequiredMixin(RoleRequiredMixin):
    """Professors and admins can access."""
    allowed_roles = ['professor', 'admin']
    permission_denied_message = 'Professor access required.'


class StudentRequiredMixin(RoleRequiredMixin):
    """Only students can access."""
    allowed_roles = ['student']
    permission_denied_message = 'Student access required.'


class ProfessorOrAdminMixin(RoleRequiredMixin):
    """Professors and admins can access."""
    allowed_roles = ['professor', 'admin']
    permission_denied_message = 'Professor or administrator access required.'


class AnyAuthenticatedMixin(LoginRequiredMixin):
    """Any authenticated user can access (just requires login)."""
    pass


# ---------------------------------------------------------------------------
# Object-level ownership mixins
# ---------------------------------------------------------------------------
class CourseProfessorMixin(ProfessorRequiredMixin):
    """
    Ensures professor can only access/edit their own courses.
    Admins bypass the check.
    Override `get_course()` to return the Course object for this view.
    """

    def get_course(self):
        """Override this to return the Course object being accessed."""
        raise NotImplementedError('Implement get_course() in your view.')

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return response
        if request.user.is_admin or request.user.is_superuser:
            return response
        try:
            course = self.get_course()
            if course.professor != request.user:
                messages.error(request, 'You can only manage your own courses.')
                return redirect('core:dashboard')
        except Exception:
            pass
        return response


class SubmissionOwnerMixin(LoginRequiredMixin):
    """
    Ensures students can only access their own submissions.
    Professors can access submissions for their courses.
    Admins can access any.
    """

    def get_submission(self):
        raise NotImplementedError('Implement get_submission() in your view.')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_admin or request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        try:
            submission = self.get_submission()

            if request.user.is_student:
                if submission.student.user != request.user:
                    messages.error(request, 'You can only view your own submissions.')
                    return redirect('core:dashboard')

            elif request.user.is_professor:
                if submission.assignment.course.professor != request.user:
                    messages.error(request, 'You can only grade submissions for your courses.')
                    return redirect('core:dashboard')

        except Exception:
            pass

        return super().dispatch(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Context Mixin — injects role info into all templates automatically
# ---------------------------------------------------------------------------
class RoleContextMixin:
    """
    Adds role flags and profile to template context.
    Include on any CBV that needs role info in templates.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            context['is_admin'] = user.is_admin or user.is_superuser
            context['is_professor'] = user.is_professor
            context['is_student'] = user.is_student

            # Attach profile if available
            if user.is_student:
                try:
                    context['student_profile'] = user.student_profile
                except Exception:
                    context['student_profile'] = None

            elif user.is_professor:
                try:
                    context['professor_profile'] = user.professor_profile
                except Exception:
                    context['professor_profile'] = None

        return context