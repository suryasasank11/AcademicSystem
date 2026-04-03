"""
accounts/decorators.py

Function-based view decorators for role-based access control.
Use these on views that use def (not class-based).

Usage:
    @login_required
    @admin_required
    def my_admin_view(request):
        ...
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------
def _role_check(role_check_fn, redirect_url='core:dashboard', message=None):
    """
    Generic decorator factory.
    role_check_fn: callable that takes user and returns bool.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not role_check_fn(request.user):
                msg = message or 'You do not have permission to access this page.'
                messages.error(request, msg)
                return redirect(redirect_url)
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


# ---------------------------------------------------------------------------
# Role decorators
# ---------------------------------------------------------------------------
def admin_required(view_func=None, redirect_url='core:dashboard'):
    """Only admin users may access this view."""
    decorator = _role_check(
        lambda u: u.is_admin or u.is_superuser,
        redirect_url=redirect_url,
        message='Administrator access required.'
    )
    if view_func:
        return decorator(view_func)
    return decorator


def professor_required(view_func=None, redirect_url='core:dashboard'):
    """Only professor (or admin) users may access this view."""
    decorator = _role_check(
        lambda u: u.is_professor or u.is_admin or u.is_superuser,
        redirect_url=redirect_url,
        message='Professor access required.'
    )
    if view_func:
        return decorator(view_func)
    return decorator


def student_required(view_func=None, redirect_url='core:dashboard'):
    """Only student users may access this view."""
    decorator = _role_check(
        lambda u: u.is_student,
        redirect_url=redirect_url,
        message='Student access required.'
    )
    if view_func:
        return decorator(view_func)
    return decorator


def professor_or_admin_required(view_func=None, redirect_url='core:dashboard'):
    """Professors and admins may access this view."""
    decorator = _role_check(
        lambda u: u.is_professor or u.is_admin or u.is_superuser,
        redirect_url=redirect_url,
        message='You need professor or admin access for this page.'
    )
    if view_func:
        return decorator(view_func)
    return decorator


def not_student_required(view_func=None, redirect_url='core:dashboard'):
    """Any logged-in non-student user may access this view."""
    decorator = _role_check(
        lambda u: not u.is_student,
        redirect_url=redirect_url,
        message='This area is not available to students.'
    )
    if view_func:
        return decorator(view_func)
    return decorator


# ---------------------------------------------------------------------------
# Object-level ownership decorator
# ---------------------------------------------------------------------------
def owns_course_or_admin(get_course_fn):
    """
    Ensures the logged-in professor owns the course being accessed,
    or the user is an admin.

    Usage:
        @professor_required
        @owns_course_or_admin(lambda request, pk: Course.objects.get(pk=pk))
        def my_view(request, pk):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_admin or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            course = get_course_fn(request, *args, **kwargs)
            if course.professor != request.user:
                messages.error(request, 'You can only manage your own courses.')
                return redirect('core:dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator