"""
assignments/views.py

Views: Assignment List/Detail/Create/Edit/Delete,
       Student Submit, Professor Grade, Submission Detail,
       Submission Comments.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Q, Count
from django.utils import timezone

from .models import Assignment, AssignmentSubmission, SubmissionComment
from .forms import (
    AssignmentForm, AssignmentSubmissionForm,
    GradeSubmissionForm, SubmissionCommentForm,
)
from apps.courses.models import Course, Enrollment
from apps.accounts.models import StudentProfile
from apps.accounts.mixins import (
    ProfessorRequiredMixin, StudentRequiredMixin,
    ProfessorOrAdminMixin, AdminRequiredMixin, RoleContextMixin,
)
from apps.accounts.decorators import professor_required, student_required


# ---------------------------------------------------------------------------
# Assignment List
# ---------------------------------------------------------------------------
class AssignmentListView(LoginRequiredMixin, RoleContextMixin, ListView):
    model = Assignment
    template_name = 'assignments/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()

        if user.is_professor:
            qs = Assignment.objects.filter(
                course__professor=user
            ).select_related('course')

        elif user.is_student:
            try:
                enrolled_courses = Enrollment.objects.filter(
                    student=user.student_profile,
                    status='enrolled'
                ).values_list('course_id', flat=True)
                qs = Assignment.objects.filter(
                    course_id__in=enrolled_courses,
                    status='published',
                ).select_related('course')
            except Exception:
                qs = Assignment.objects.none()

        else:  # admin
            qs = Assignment.objects.all().select_related('course', 'created_by')

        # Filters
        course_id = self.request.GET.get('course', '')
        status = self.request.GET.get('status', '')
        atype = self.request.GET.get('type', '')
        due = self.request.GET.get('due', '')
        q = self.request.GET.get('q', '').strip()

        if course_id:
            qs = qs.filter(course_id=course_id)
        if status:
            qs = qs.filter(status=status)
        if atype:
            qs = qs.filter(assignment_type=atype)
        if due == 'upcoming':
            qs = qs.filter(due_date__gte=now)
        elif due == 'overdue':
            qs = qs.filter(due_date__lt=now)
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(course__course_code__icontains=q)
            )

        return qs.order_by('due_date')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_professor:
            ctx['courses'] = Course.objects.filter(professor=user, is_active=True)
        elif user.is_admin or user.is_superuser:
            ctx['courses'] = Course.objects.filter(is_active=True)
        ctx['type_choices'] = Assignment.TYPE_CHOICES
        ctx['status_choices'] = Assignment.STATUS_CHOICES
        ctx['filter_course'] = self.request.GET.get('course', '')
        ctx['filter_status'] = self.request.GET.get('status', '')
        ctx['filter_type'] = self.request.GET.get('type', '')
        ctx['filter_due'] = self.request.GET.get('due', '')
        ctx['search_query'] = self.request.GET.get('q', '')
        return ctx


# ---------------------------------------------------------------------------
# Assignment Detail
# ---------------------------------------------------------------------------
class AssignmentDetailView(LoginRequiredMixin, RoleContextMixin, DetailView):
    model = Assignment
    template_name = 'assignments/assignment_detail.html'
    context_object_name = 'assignment'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        assignment = self.get_object()
        user = self.request.user

        if user.is_student:
            try:
                student = user.student_profile
                ctx['my_submission'] = assignment.get_student_submission(student)
                ctx['submission_form'] = AssignmentSubmissionForm()
                ctx['can_submit'] = (
                    assignment.status == 'published' and
                    (not assignment.is_overdue or assignment.late_submission_allowed)
                )
                # Check enrollment
                ctx['is_enrolled'] = Enrollment.objects.filter(
                    student=student,
                    course=assignment.course,
                    status='enrolled'
                ).exists()
            except Exception:
                pass

        elif user.is_professor or user.is_admin:
            ctx['submissions'] = assignment.submissions.select_related(
                'student__user'
            ).order_by('-submitted_at')
            ctx['submission_count'] = assignment.submission_count
            ctx['graded_count'] = assignment.graded_count
            ctx['pending_count'] = assignment.pending_grading_count

        return ctx


# ---------------------------------------------------------------------------
# Assignment Create
# ---------------------------------------------------------------------------
class AssignmentCreateView(ProfessorOrAdminMixin, RoleContextMixin, CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignments/assignment_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['professor'] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        course_pk = self.kwargs.get('course_pk')
        if course_pk:
            initial['course'] = course_pk
        initial['assigned_date'] = timezone.now()
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action'] = 'Create'
        return ctx

    def form_valid(self, form):
        assignment = form.save(commit=False)
        assignment.created_by = self.request.user
        assignment.save()
        messages.success(
            self.request,
            f'Assignment "{assignment.title}" created successfully.'
        )
        return redirect('assignments:detail', pk=assignment.pk)


# ---------------------------------------------------------------------------
# Assignment Update
# ---------------------------------------------------------------------------
class AssignmentUpdateView(ProfessorOrAdminMixin, RoleContextMixin, UpdateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignments/assignment_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['professor'] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        assignment = self.get_object()
        if request.user.is_professor and assignment.created_by != request.user:
            messages.error(request, 'You can only edit your own assignments.')
            return redirect('assignments:list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action'] = 'Edit'
        return ctx

    def form_valid(self, form):
        assignment = form.save()
        messages.success(self.request, f'Assignment "{assignment.title}" updated.')
        return redirect('assignments:detail', pk=assignment.pk)


# ---------------------------------------------------------------------------
# Assignment Delete
# ---------------------------------------------------------------------------
class AssignmentDeleteView(ProfessorOrAdminMixin, RoleContextMixin, DeleteView):
    model = Assignment
    template_name = 'assignments/assignment_confirm_delete.html'
    success_url = reverse_lazy('assignments:list')

    def dispatch(self, request, *args, **kwargs):
        assignment = self.get_object()
        if request.user.is_professor and assignment.created_by != request.user:
            messages.error(request, 'Permission denied.')
            return redirect('assignments:list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        title = self.get_object().title
        response = super().form_valid(form)
        messages.success(self.request, f'Assignment "{title}" deleted.')
        return response


# ---------------------------------------------------------------------------
# Student: Submit Assignment
# ---------------------------------------------------------------------------
@login_required
def submit_assignment_view(request, pk):
    """Student submits their work for an assignment."""
    assignment = get_object_or_404(Assignment, pk=pk)
    user = request.user

    if not user.is_student:
        messages.error(request, 'Students only.')
        return redirect('assignments:detail', pk=pk)

    try:
        student = user.student_profile
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('core:dashboard')

    # Check enrollment
    is_enrolled = Enrollment.objects.filter(
        student=student, course=assignment.course, status='enrolled'
    ).exists()
    if not is_enrolled:
        messages.error(request, 'You are not enrolled in this course.')
        return redirect('assignments:list')

    # Check if assignment is open
    if assignment.status != 'published':
        messages.error(request, 'This assignment is not open for submission.')
        return redirect('assignments:detail', pk=pk)

    now = timezone.now()
    is_late = now > assignment.due_date
    if is_late and not assignment.late_submission_allowed:
        messages.error(request, 'The deadline has passed and late submissions are not accepted.')
        return redirect('assignments:detail', pk=pk)

    # Find or create submission (handle resubmission)
    existing = assignment.get_student_submission(student)
    if existing and not assignment.allow_resubmission:
        messages.warning(request, 'You have already submitted this assignment.')
        return redirect('assignments:submission_detail', pk=existing.pk)

    # Check max submissions
    submission_count = AssignmentSubmission.objects.filter(
        assignment=assignment, student=student
    ).count()
    if submission_count >= assignment.max_submissions:
        messages.error(
            request,
            f'Maximum submissions ({assignment.max_submissions}) reached.'
        )
        return redirect('assignments:detail', pk=pk)

    form = AssignmentSubmissionForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        submission = form.save(commit=False)
        submission.assignment = assignment
        submission.student = student
        submission.submitted_at = now
        submission.submission_number = submission_count + 1
        submission.status = 'submitted'

        if is_late:
            submission.is_late = True
            submission.status = 'late'

        submission.save()
        messages.success(
            request,
            f'Assignment "{assignment.title}" submitted successfully!'
            + (' (marked as late)' if is_late else '')
        )
        return redirect('assignments:submission_detail', pk=submission.pk)

    return render(request, 'assignments/submit_assignment.html', {
        'assignment': assignment,
        'form': form,
        'is_late': is_late,
        'existing': existing,
    })


# ---------------------------------------------------------------------------
# Submission Detail
# ---------------------------------------------------------------------------
class SubmissionDetailView(LoginRequiredMixin, RoleContextMixin, DetailView):
    model = AssignmentSubmission
    template_name = 'assignments/submission_detail.html'
    context_object_name = 'submission'

    def dispatch(self, request, *args, **kwargs):
        sub = self.get_object()
        user = request.user
        if user.is_student:
            if not hasattr(user, 'student_profile') or sub.student != user.student_profile:
                messages.error(request, 'Permission denied.')
                return redirect('core:dashboard')
        elif user.is_professor:
            if sub.assignment.course.professor != user:
                messages.error(request, 'Permission denied.')
                return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sub = self.get_object()
        user = self.request.user
        ctx['comment_form'] = SubmissionCommentForm()
        # Filter private comments for students
        if user.is_student:
            ctx['comments'] = sub.comments.filter(is_private=False)
        else:
            ctx['comments'] = sub.comments.all()
        if user.is_professor or user.is_admin:
            ctx['grade_form'] = GradeSubmissionForm(
                instance=sub, assignment=sub.assignment
            )
        return ctx


# ---------------------------------------------------------------------------
# Professor: Grade a Submission
# ---------------------------------------------------------------------------
@professor_required
def grade_submission_view(request, pk):
    """Professor grades a student's submission."""
    submission = get_object_or_404(
        AssignmentSubmission.objects.select_related(
            'assignment__course', 'student__user'
        ),
        pk=pk
    )
    user = request.user

    if user.is_professor and submission.assignment.course.professor != user:
        messages.error(request, 'Permission denied.')
        return redirect('assignments:list')

    form = GradeSubmissionForm(
        request.POST or None,
        instance=submission,
        assignment=submission.assignment
    )

    if request.method == 'POST' and form.is_valid():
        sub = form.save(commit=False)
        sub.graded_by = user
        sub.graded_at = timezone.now()
        sub.save()
        messages.success(
            request,
            f'Submission graded: {sub.score}/{sub.assignment.max_score} for '
            f'{sub.student.user.get_full_name()}.'
        )
        return redirect('assignments:submission_detail', pk=pk)

    return render(request, 'assignments/grade_submission.html', {
        'form': form,
        'submission': submission,
    })


# ---------------------------------------------------------------------------
# Submission Comment
# ---------------------------------------------------------------------------
@login_required
def add_submission_comment_view(request, submission_pk):
    """Add a comment to a submission (both professor and student)."""
    submission = get_object_or_404(AssignmentSubmission, pk=submission_pk)
    user = request.user

    # Permission check
    is_student_owner = (
        user.is_student and
        hasattr(user, 'student_profile') and
        submission.student == user.student_profile
    )
    is_course_professor = (
        user.is_professor and
        submission.assignment.course.professor == user
    )
    is_admin = user.is_admin or user.is_superuser

    if not (is_student_owner or is_course_professor or is_admin):
        messages.error(request, 'Permission denied.')
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = SubmissionCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.submission = submission
            comment.author = user
            # Students can't make private comments
            if user.is_student:
                comment.is_private = False
            comment.save()
            messages.success(request, 'Comment added.')
        else:
            messages.error(request, 'Invalid comment.')

    return redirect('assignments:submission_detail', pk=submission_pk)


# ---------------------------------------------------------------------------
# Professor: All Submissions for an Assignment
# ---------------------------------------------------------------------------
@professor_required
def assignment_submissions_view(request, pk):
    """View all submissions for an assignment."""
    assignment = get_object_or_404(Assignment, pk=pk)
    user = request.user

    if user.is_professor and assignment.course.professor != user:
        messages.error(request, 'Permission denied.')
        return redirect('assignments:list')

    submissions = assignment.submissions.select_related(
        'student__user'
    ).order_by('-submitted_at')

    # Filters
    graded = request.GET.get('graded', '')
    status = request.GET.get('status', '')
    if graded == '1':
        submissions = submissions.filter(is_graded=True)
    elif graded == '0':
        submissions = submissions.filter(is_graded=False)
    if status:
        submissions = submissions.filter(status=status)

    # Enrolled students who haven't submitted
    enrolled_ids = Enrollment.objects.filter(
        course=assignment.course, status='enrolled'
    ).values_list('student_id', flat=True)
    submitted_ids = assignment.submissions.values_list('student_id', flat=True)
    not_submitted = StudentProfile.objects.filter(
        id__in=enrolled_ids
    ).exclude(id__in=submitted_ids).select_related('user')

    return render(request, 'assignments/assignment_submissions.html', {
        'assignment': assignment,
        'submissions': submissions,
        'not_submitted': not_submitted,
        'filter_graded': graded,
        'filter_status': status,
        'status_choices': AssignmentSubmission.STATUS_CHOICES,
    })


# ---------------------------------------------------------------------------
# Publish / Close Assignment (toggle)
# ---------------------------------------------------------------------------
@professor_required
def toggle_assignment_status_view(request, pk):
    """Publish or close an assignment."""
    assignment = get_object_or_404(Assignment, pk=pk)
    user = request.user

    if user.is_professor and assignment.created_by != user:
        messages.error(request, 'Permission denied.')
        return redirect('assignments:list')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'publish' and assignment.status == 'draft':
            assignment.status = 'published'
            messages.success(request, f'"{assignment.title}" is now published.')
        elif action == 'close':
            assignment.status = 'closed'
            messages.success(request, f'"{assignment.title}" is now closed.')
        elif action == 'reopen':
            assignment.status = 'published'
            messages.success(request, f'"{assignment.title}" reopened.')
        assignment.save()

    return redirect('assignments:detail', pk=pk)