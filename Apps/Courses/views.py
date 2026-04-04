"""
courses/views.py

Views: Course List/Detail/Create/Edit/Delete,
       Enrollment management, Announcement CRUD,
       Student self-enrollment.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse

from .models import Course, Enrollment, Announcement
from .forms import (
    CourseForm, EnrollmentForm, SelfEnrollForm, AnnouncementForm
)
from apps.accounts.models import StudentProfile
from apps.accounts.mixins import (
    AdminRequiredMixin, ProfessorRequiredMixin,
    ProfessorOrAdminMixin, RoleContextMixin, AnyAuthenticatedMixin,
)
from apps.accounts.decorators import admin_required, professor_required


# ---------------------------------------------------------------------------
# Course Views
# ---------------------------------------------------------------------------
class CourseListView(LoginRequiredMixin, RoleContextMixin, ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 12

    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.select_related(
            'professor', 'department'
        ).annotate(
            enrolled_count=Count(
                'enrollments',
                filter=Q(enrollments__status='enrolled')
            )
        )

        # Professors only see their own courses
        if user.is_professor:
            qs = qs.filter(professor=user)

        # Filter params
        q = self.request.GET.get('q', '').strip()
        semester = self.request.GET.get('semester', '').strip()
        year = self.request.GET.get('year', '').strip()
        status = self.request.GET.get('status', '').strip()
        dept = self.request.GET.get('dept', '').strip()

        if q:
            qs = qs.filter(
                Q(course_code__icontains=q) |
                Q(title__icontains=q) |
                Q(professor__first_name__icontains=q) |
                Q(professor__last_name__icontains=q)
            )
        if semester:
            qs = qs.filter(semester=semester)
        if year:
            qs = qs.filter(academic_year=year)
        if status:
            qs = qs.filter(status=status)
        if dept:
            qs = qs.filter(department_id=dept)

        return qs.order_by('-academic_year', 'semester', 'course_code')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.accounts.models import Department
        ctx['departments'] = Department.objects.all()
        ctx['semester_choices'] = Course.objects.values_list(
            'semester', flat=True
        ).distinct()
        ctx['year_choices'] = Course.objects.values_list(
            'academic_year', flat=True
        ).distinct().order_by('-academic_year')
        ctx['search_query'] = self.request.GET.get('q', '')
        ctx['filter_semester'] = self.request.GET.get('semester', '')
        ctx['filter_year'] = self.request.GET.get('year', '')
        ctx['filter_status'] = self.request.GET.get('status', '')
        return ctx


class CourseDetailView(LoginRequiredMixin, RoleContextMixin, DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        course = self.get_object()
        user = self.request.user

        ctx['announcements'] = course.announcements.filter(
            publish_at__lte=timezone.now()
        ).order_by('-is_pinned', '-publish_at')[:10]

        ctx['assignments'] = course.assignments.filter(
            status='published'
        ).order_by('due_date')[:10]

        # Enrollment info
        ctx['enrollments'] = course.enrollments.filter(
            status='enrolled'
        ).select_related('student__user').order_by(
            'student__student_id'
        )

        # Student-specific: is this student enrolled?
        if user.is_student:
            try:
                sp = user.student_profile
                ctx['my_enrollment'] = Enrollment.objects.filter(
                    student=sp, course=course
                ).first()
                ctx['can_enroll'] = not course.is_full and not ctx['my_enrollment']
                ctx['enroll_form'] = SelfEnrollForm(student=sp)
            except StudentProfile.DoesNotExist:
                pass

        # Grade components
        ctx['grade_components'] = course.grade_components.all()

        # Attendance sessions
        ctx['recent_sessions'] = course.attendance_sessions.order_by('-date')[:5]

        return ctx


class CourseCreateView(ProfessorOrAdminMixin, RoleContextMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action'] = 'Create'
        return ctx

    def form_valid(self, form):
        course = form.save(commit=False)
        if self.request.user.is_professor:
            course.professor = self.request.user
        course.save()
        messages.success(self.request, f'Course "{course.title}" created successfully.')
        return redirect('courses:detail', pk=course.pk)


class CourseUpdateView(ProfessorOrAdminMixin, RoleContextMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        course = self.get_object()
        if request.user.is_professor and course.professor != request.user:
            messages.error(request, 'You can only edit your own courses.')
            return redirect('courses:list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action'] = 'Edit'
        return ctx

    def form_valid(self, form):
        course = form.save()
        messages.success(self.request, f'Course "{course.title}" updated.')
        return redirect('courses:detail', pk=course.pk)


class CourseDeleteView(AdminRequiredMixin, RoleContextMixin, DeleteView):
    model = Course
    template_name = 'courses/course_confirm_delete.html'
    success_url = reverse_lazy('courses:list')

    def form_valid(self, form):
        title = self.get_object().title
        response = super().form_valid(form)
        messages.success(self.request, f'Course "{title}" deleted.')
        return response


# ---------------------------------------------------------------------------
# Enrollment Views
# ---------------------------------------------------------------------------
class EnrollmentListView(ProfessorOrAdminMixin, RoleContextMixin, ListView):
    model = Enrollment
    template_name = 'courses/enrollment_list.html'
    context_object_name = 'enrollments'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Enrollment.objects.select_related(
            'student__user', 'course', 'course__professor'
        )
        if user.is_professor:
            qs = qs.filter(course__professor=user)

        # Filters
        course_id = self.request.GET.get('course', '')
        status = self.request.GET.get('status', '')
        q = self.request.GET.get('q', '').strip()

        if course_id:
            qs = qs.filter(course_id=course_id)
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(student__user__first_name__icontains=q) |
                Q(student__user__last_name__icontains=q) |
                Q(student__student_id__icontains=q)
            )
        return qs.order_by('-enrollment_date')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_professor:
            ctx['course_list'] = Course.objects.filter(professor=user, is_active=True)
        else:
            ctx['course_list'] = Course.objects.filter(is_active=True)
        ctx['status_choices'] = Enrollment.STATUS_CHOICES
        ctx['filter_course'] = self.request.GET.get('course', '')
        ctx['filter_status'] = self.request.GET.get('status', '')
        ctx['search_query'] = self.request.GET.get('q', '')
        return ctx


@login_required
def enroll_student_view(request, course_pk):
    """Admin or professor enrolls a specific student in a course."""
    course = get_object_or_404(Course, pk=course_pk)
    user = request.user

    if not (user.is_admin or user.is_superuser or
            (user.is_professor and course.professor == user)):
        messages.error(request, 'Permission denied.')
        return redirect('courses:detail', pk=course_pk)

    form = EnrollmentForm(request.POST or None, course=course)
    if request.method == 'POST' and form.is_valid():
        enrollment = form.save(commit=False)
        enrollment.course = course
        enrollment.save()

        # Create attendance summary
        from apps.attendance.models import AttendanceSummary
        AttendanceSummary.objects.get_or_create(enrollment=enrollment)

        messages.success(
            request,
            f'{enrollment.student.user.get_full_name()} enrolled in {course.course_code}.'
        )
        return redirect('courses:detail', pk=course_pk)

    return render(request, 'courses/enroll_student.html', {
        'course': course,
        'form': form,
    })


@login_required
def self_enroll_view(request):
    """Student self-enrolls in a course."""
    if not request.user.is_student:
        messages.error(request, 'Only students can self-enroll.')
        return redirect('core:dashboard')

    try:
        student = request.user.student_profile
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('core:dashboard')

    form = SelfEnrollForm(request.POST or None, student=student)
    if request.method == 'POST' and form.is_valid():
        course = form.cleaned_data['course']
        status = 'waitlisted' if course.is_full else 'enrolled'
        enrollment, created = Enrollment.objects.get_or_create(
            student=student,
            course=course,
            defaults={'status': status}
        )
        if created:
            from apps.attendance.models import AttendanceSummary
            AttendanceSummary.objects.get_or_create(enrollment=enrollment)
            msg = (f'Successfully enrolled in {course.course_code}.'
                   if status == 'enrolled'
                   else f'Added to waitlist for {course.course_code}.')
            messages.success(request, msg)
        else:
            messages.warning(request, f'You are already enrolled in {course.course_code}.')
        return redirect('courses:detail', pk=course.pk)

    return render(request, 'courses/self_enroll.html', {
        'form': form,
        'available_courses': Course.objects.filter(
            is_active=True, status='active'
        ).order_by('course_code'),
    })


@login_required
def drop_enrollment_view(request, pk):
    """Student drops a course, or admin/professor drops a student."""
    enrollment = get_object_or_404(Enrollment, pk=pk)
    user = request.user

    # Permission check
    is_own = (user.is_student and
              hasattr(user, 'student_profile') and
              enrollment.student == user.student_profile)
    is_professor_of_course = (user.is_professor and
                               enrollment.course.professor == user)
    is_admin = user.is_admin or user.is_superuser

    if not (is_own or is_professor_of_course or is_admin):
        messages.error(request, 'Permission denied.')
        return redirect('core:dashboard')

    if request.method == 'POST':
        enrollment.status = 'dropped'
        enrollment.drop_date = timezone.now()
        enrollment.save()
        messages.success(
            request,
            f'Dropped {enrollment.student.user.get_full_name()} from {enrollment.course.course_code}.'
        )
        if is_own:
            return redirect('core:dashboard')
        return redirect('courses:detail', pk=enrollment.course.pk)

    return render(request, 'courses/drop_enrollment.html', {'enrollment': enrollment})


@login_required
def update_enrollment_status_view(request, pk):
    """Admin/professor updates enrollment status."""
    enrollment = get_object_or_404(Enrollment, pk=pk)
    user = request.user

    if not (user.is_admin or user.is_superuser or
            (user.is_professor and enrollment.course.professor == user)):
        messages.error(request, 'Permission denied.')
        return redirect('core:dashboard')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Enrollment.STATUS_CHOICES):
            enrollment.status = new_status
            if new_status == 'dropped':
                enrollment.drop_date = timezone.now()
            elif new_status == 'completed':
                enrollment.completion_date = timezone.now()
            enrollment.save()
            messages.success(request, 'Enrollment status updated.')
        return redirect(request.POST.get('next', 'courses:enrollment_list'))

    return render(request, 'courses/update_enrollment.html', {
        'enrollment': enrollment,
        'status_choices': Enrollment.STATUS_CHOICES,
    })


# ---------------------------------------------------------------------------
# Announcement Views
# ---------------------------------------------------------------------------
class AnnouncementListView(LoginRequiredMixin, RoleContextMixin, ListView):
    model = Announcement
    template_name = 'courses/announcement_list.html'
    context_object_name = 'announcements'
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()
        qs = Announcement.objects.select_related('course', 'author')

        if user.is_professor:
            qs = qs.filter(course__professor=user)
        elif user.is_student:
            try:
                enrolled_courses = Enrollment.objects.filter(
                    student=user.student_profile,
                    status='enrolled'
                ).values_list('course_id', flat=True)
                qs = qs.filter(
                    course_id__in=enrolled_courses,
                    publish_at__lte=now,
                )
            except Exception:
                qs = qs.none()

        return qs.order_by('-is_pinned', '-publish_at')


class AnnouncementDetailView(LoginRequiredMixin, RoleContextMixin, DetailView):
    model = Announcement
    template_name = 'courses/announcement_detail.html'
    context_object_name = 'announcement'


class AnnouncementCreateView(ProfessorOrAdminMixin, RoleContextMixin, CreateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'courses/announcement_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action'] = 'Create'
        course_pk = self.kwargs.get('course_pk')
        if course_pk:
            ctx['course'] = get_object_or_404(Course, pk=course_pk)
        return ctx

    def form_valid(self, form):
        ann = form.save(commit=False)
        ann.author = self.request.user
        course_pk = self.kwargs.get('course_pk')
        if course_pk:
            ann.course = get_object_or_404(Course, pk=course_pk)
        ann.save()
        messages.success(self.request, f'Announcement "{ann.title}" published.')
        return redirect('courses:detail', pk=ann.course.pk)


class AnnouncementUpdateView(ProfessorOrAdminMixin, RoleContextMixin, UpdateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'courses/announcement_form.html'

    def dispatch(self, request, *args, **kwargs):
        ann = self.get_object()
        if request.user.is_professor and ann.author != request.user:
            messages.error(request, 'You can only edit your own announcements.')
            return redirect('courses:list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action'] = 'Edit'
        return ctx

    def form_valid(self, form):
        ann = form.save()
        messages.success(self.request, 'Announcement updated.')
        return redirect('courses:detail', pk=ann.course.pk)


class AnnouncementDeleteView(ProfessorOrAdminMixin, RoleContextMixin, DeleteView):
    model = Announcement
    template_name = 'courses/announcement_confirm_delete.html'

    def get_success_url(self):
        return reverse('courses:detail', kwargs={'pk': self.object.course.pk})

    def form_valid(self, form):
        title = self.get_object().title
        course_pk = self.get_object().course.pk
        response = super().form_valid(form)
        messages.success(self.request, f'Announcement "{title}" deleted.')
        return response