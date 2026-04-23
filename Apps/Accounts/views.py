"""
accounts/views.py

Views: Login, Logout, Register, Profile, Password Change,
       User List/Create/Edit/Delete (admin),
       Student & Professor management (admin).
"""
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import User
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404

from .models import User, UserRole, StudentProfile, ProfessorProfile, Department
from .forms import (
    LoginForm, UserRegistrationForm, UserEditForm, ProfileEditForm,
    CustomPasswordChangeForm, StudentProfileForm, ProfessorProfileForm,
    DepartmentForm,
)
from .mixins import AdminRequiredMixin, RoleContextMixin
from .decorators import admin_required


# ---------------------------------------------------------------------------
# Authentication Views
# ---------------------------------------------------------------------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            # Handle remember me
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)
            login(request, user)
            # Store IP
            ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
            if ip:
                user.last_login_ip = ip.split(',')[0].strip()
                user.save(update_fields=['last_login_ip'])
            messages.success(request, f'Welcome back, {user.get_short_name()}!')
            next_url = request.GET.get('next', 'core:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password. Please try again.')

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    name = request.user.get_short_name()
    logout(request)
    messages.info(request, f'You have been logged out, {name}. See you soon!')
    return redirect('accounts:login')


def register_view(request):
    """Public registration — only for students by default."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    form = UserRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.role = UserRole.STUDENT  # Public registration always creates students
        user.save()
        # Auto-create student profile
        StudentProfile.objects.create(
            user=user,
            student_id=f'STU-{timezone.now().year}-{user.pk:04d}',
        )
        login(request, user)
        messages.success(request, 'Account created successfully! Welcome to the Academic System.')
        return redirect('core:dashboard')

    return render(request, 'accounts/register.html', {'form': form})


# ---------------------------------------------------------------------------
# Profile Views
# ---------------------------------------------------------------------------
@login_required
def profile_view(request):
    """Current user's own profile."""
    user = request.user
    profile = None
    if user.is_student:
        try:
            profile = user.student_profile
        except StudentProfile.DoesNotExist:
            pass
    elif user.is_professor:
        try:
            profile = user.professor_profile
        except ProfessorProfile.DoesNotExist:
            pass

    return render(request, 'accounts/profile.html', {
        'profile_user': user,
        'profile': profile,
    })


@login_required
def profile_edit_view(request):
    """Edit own profile."""
    form = ProfileEditForm(
        request.POST or None,
        request.FILES or None,
        instance=request.user
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('accounts:profile')

    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
def change_password_view(request):
    form = CustomPasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password changed successfully.')
        return redirect('accounts:profile')

    return render(request, 'accounts/change_password.html', {'form': form})


# ---------------------------------------------------------------------------
# Admin — User Management
# ---------------------------------------------------------------------------
class UserListView(AdminRequiredMixin, RoleContextMixin, ListView):
    model = User
    template_name = 'accounts/admin/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.all().order_by('role', 'last_name', 'first_name')
        q = self.request.GET.get('q', '').strip()
        role = self.request.GET.get('role', '').strip()
        status = self.request.GET.get('status', '').strip()

        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q)
            )
        if role:
            qs = qs.filter(role=role)
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_users'] = User.objects.count()
        ctx['total_students'] = User.objects.filter(role=UserRole.STUDENT).count()
        ctx['total_professors'] = User.objects.filter(role=UserRole.PROFESSOR).count()
        ctx['total_admins'] = User.objects.filter(role=UserRole.ADMIN).count()
        ctx['search_query'] = self.request.GET.get('q', '')
        ctx['role_filter'] = self.request.GET.get('role', '')
        ctx['status_filter'] = self.request.GET.get('status', '')
        ctx['role_choices'] = UserRole.choices
        return ctx


class UserCreateView(AdminRequiredMixin, RoleContextMixin, CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/admin/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action'] = 'Create'
        ctx['student_form'] = StudentProfileForm(self.request.POST or None)
        ctx['professor_form'] = ProfessorProfileForm(self.request.POST or None)
        return ctx

    def form_valid(self, form):
        user = form.save()
        role = user.role

        if role == UserRole.STUDENT:
            s_form = StudentProfileForm(self.request.POST)
            if s_form.is_valid():
                profile = s_form.save(commit=False)
                profile.user = user
                profile.save()
            else:
                StudentProfile.objects.create(
                    user=user,
                    student_id=f'STU-{timezone.now().year}-{user.pk:04d}',
                )

        elif role == UserRole.PROFESSOR:
            p_form = ProfessorProfileForm(self.request.POST)
            if p_form.is_valid():
                profile = p_form.save(commit=False)
                profile.user = user
                profile.save()
            else:
                ProfessorProfile.objects.create(
                    user=user,
                    employee_id=f'EMP-{timezone.now().year}-{user.pk:04d}',
                )

        messages.success(self.request, f'User "{user.get_full_name()}" created successfully.')
        return redirect(self.success_url)


class UserEditView(AdminRequiredMixin, RoleContextMixin, UpdateView):
    model = User
    form_class = UserEditForm
    template_name = 'accounts/admin/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action'] = 'Edit'
        user = self.get_object()
        if user.is_student:
            profile = getattr(user, 'student_profile', None)
            ctx['student_form'] = StudentProfileForm(
                self.request.POST or None, instance=profile
            )
        elif user.is_professor:
            profile = getattr(user, 'professor_profile', None)
            ctx['professor_form'] = ProfessorProfileForm(
                self.request.POST or None, instance=profile
            )
        return ctx

    def form_valid(self, form):
        user = form.save()
        if user.is_student:
            profile = getattr(user, 'student_profile', None)
            s_form = StudentProfileForm(self.request.POST, instance=profile)
            if s_form.is_valid():
                p = s_form.save(commit=False)
                p.user = user
                p.save()
        elif user.is_professor:
            profile = getattr(user, 'professor_profile', None)
            p_form = ProfessorProfileForm(self.request.POST, instance=profile)
            if p_form.is_valid():
                p = p_form.save(commit=False)
                p.user = user
                p.save()

        messages.success(self.request, f'User "{user.get_full_name()}" updated successfully.')
        return redirect(self.success_url)


class UserDeleteView(LoginRequiredMixin, View):

    def get(self, request, pk):
        user_to_delete = get_object_or_404(User, pk=pk)
        return render(request, 'accounts/admin/user_confirm_delete.html', {
            'object': user_to_delete
        })
    def post(self, request, pk):
        user_to_delete = get_object_or_404(User, pk=pk)

        if user_to_delete.pk == request.user.pk:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('accounts:user_list')

        name = user_to_delete.get_full_name()

        # Step 1 — Remove as department head
        from apps.accounts.models import Department
        Department.objects.filter(head=user_to_delete).update(head=None)

        # Step 2 — Delete all courses taught by this professor
        # (this also cascades to enrollments, grades, attendance, assignments)
        if user_to_delete.is_professor:
            from apps.courses.models import Course
            Course.objects.filter(professor=user_to_delete).delete()

        # Step 3 — Now safe to delete the user
        user_to_delete.delete()
        messages.success(request, f'User "{name}" and all associated data deleted successfully.')
        return redirect('accounts:user_list')
class UserDetailView(AdminRequiredMixin, RoleContextMixin, DetailView):
    model = User
    template_name = 'accounts/admin/user_detail.html'
    context_object_name = 'profile_user'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.get_object()
        if user.is_student:
            try:
                ctx['student_profile'] = user.student_profile
                ctx['enrollments'] = user.student_profile.enrollments.select_related(
                    'course', 'course__professor'
                ).order_by('-enrollment_date')[:10]
            except StudentProfile.DoesNotExist:
                pass
        elif user.is_professor:
            try:
                ctx['professor_profile'] = user.professor_profile
                ctx['courses'] = user.taught_courses.filter(
                    is_active=True
                ).order_by('-academic_year', 'semester')[:10]
            except ProfessorProfile.DoesNotExist:
                pass
        return ctx


# ---------------------------------------------------------------------------
# Admin — Department Management
# ---------------------------------------------------------------------------
class DepartmentListView(AdminRequiredMixin, RoleContextMixin, ListView):
    model = Department
    template_name = 'accounts/admin/department_list.html'
    context_object_name = 'departments'
    ordering = ['name']


class DepartmentCreateView(AdminRequiredMixin, RoleContextMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'accounts/admin/department_form.html'
    success_url = reverse_lazy('accounts:department_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action'] = 'Create'
        return ctx

    def form_valid(self, form):
        dept = form.save()
        messages.success(self.request, f'Department "{dept.name}" created.')
        return redirect(self.success_url)


class DepartmentUpdateView(AdminRequiredMixin, RoleContextMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'accounts/admin/department_form.html'
    success_url = reverse_lazy('accounts:department_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action'] = 'Edit'
        return ctx

    def form_valid(self, form):
        dept = form.save()
        messages.success(self.request, f'Department "{dept.name}" updated.')
        return redirect(self.success_url)


class DepartmentDeleteView(AdminRequiredMixin, RoleContextMixin, DeleteView):
    model = Department
    template_name = 'accounts/admin/department_confirm_delete.html'
    success_url = reverse_lazy('accounts:department_list')

    def form_valid(self, form):
        name = self.get_object().name
        response = super().form_valid(form)
        messages.success(self.request, f'Department "{name}" deleted.')
        return response


# ---------------------------------------------------------------------------
# AJAX helpers
# ---------------------------------------------------------------------------
@login_required
def toggle_user_active(request, pk):
    """AJAX endpoint to toggle user active status."""
    if not (request.user.is_admin or request.user.is_superuser):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        return JsonResponse({'error': 'Cannot deactivate yourself'}, status=400)

    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    return JsonResponse({'is_active': user.is_active})