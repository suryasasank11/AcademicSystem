"""
grades/views.py

Views: Grade List, Grade Detail, Grade Entry (single + bulk),
       Grade Components, Student Grade Report, GPA tracking.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, UpdateView
from django.db.models import Q, Avg
from django.utils import timezone
from django.http import JsonResponse

from .models import Grade, GradeComponent, GradeHistory
from .forms import GradeForm, BulkGradeEntryForm, GradeComponentForm, GradeComponentFormSet
from apps.courses.models import Course, Enrollment
from apps.accounts.models import StudentProfile
from apps.accounts.mixins import (
    ProfessorRequiredMixin, StudentRequiredMixin,
    ProfessorOrAdminMixin, AdminRequiredMixin, RoleContextMixin,
)
from apps.accounts.decorators import professor_required, admin_required


# ---------------------------------------------------------------------------
# Grade List — Professor/Admin sees all grades
# ---------------------------------------------------------------------------
class GradeListView(ProfessorOrAdminMixin, RoleContextMixin, ListView):
    model = Grade
    template_name = 'grades/grade_list.html'
    context_object_name = 'grades'
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        qs = Grade.objects.select_related(
            'enrollment__student__user',
            'enrollment__course',
            'graded_by',
        )
        if user.is_professor:
            qs = qs.filter(enrollment__course__professor=user)

        # Filters
        course_id = self.request.GET.get('course', '')
        finalized = self.request.GET.get('finalized', '')
        letter = self.request.GET.get('letter', '')
        q = self.request.GET.get('q', '').strip()

        if course_id:
            qs = qs.filter(enrollment__course_id=course_id)
        if finalized == '1':
            qs = qs.filter(is_finalized=True)
        elif finalized == '0':
            qs = qs.filter(is_finalized=False)
        if letter:
            qs = qs.filter(letter_grade__startswith=letter)
        if q:
            qs = qs.filter(
                Q(enrollment__student__user__first_name__icontains=q) |
                Q(enrollment__student__user__last_name__icontains=q) |
                Q(enrollment__student__student_id__icontains=q)
            )
        return qs.order_by('-graded_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_professor:
            ctx['courses'] = Course.objects.filter(professor=user, is_active=True)
        else:
            ctx['courses'] = Course.objects.filter(is_active=True)
        ctx['filter_course'] = self.request.GET.get('course', '')
        ctx['filter_finalized'] = self.request.GET.get('finalized', '')
        ctx['filter_letter'] = self.request.GET.get('letter', '')
        ctx['search_query'] = self.request.GET.get('q', '')
        return ctx


# ---------------------------------------------------------------------------
# Grade Detail
# ---------------------------------------------------------------------------
class GradeDetailView(LoginRequiredMixin, RoleContextMixin, DetailView):
    model = Grade
    template_name = 'grades/grade_detail.html'
    context_object_name = 'grade'

    def dispatch(self, request, *args, **kwargs):
        grade = self.get_object()
        user = request.user
        if user.is_student:
            if not hasattr(user, 'student_profile') or \
               grade.enrollment.student != user.student_profile:
                messages.error(request, 'You can only view your own grades.')
                return redirect('core:dashboard')
        elif user.is_professor:
            if grade.enrollment.course.professor != user:
                messages.error(request, 'Permission denied.')
                return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['history'] = self.get_object().history.all()
        return ctx


# ---------------------------------------------------------------------------
# Single Grade Entry / Edit
# ---------------------------------------------------------------------------
@professor_required
def grade_entry_view(request, enrollment_pk):
    """Enter or edit grade for a single student enrollment."""
    enrollment = get_object_or_404(
        Enrollment.objects.select_related('student__user', 'course'),
        pk=enrollment_pk
    )
    user = request.user

    # Professor can only grade their own courses
    if user.is_professor and enrollment.course.professor != user:
        messages.error(request, 'You can only grade students in your own courses.')
        return redirect('grades:list')

    # Get or create grade instance
    grade, created = Grade.objects.get_or_create(
        enrollment=enrollment,
        defaults={'graded_by': user}
    )

    # Save history snapshot before editing
    old_score = grade.numeric_score
    old_letter = grade.letter_grade

    form = GradeForm(request.POST or None, instance=grade)
    if request.method == 'POST' and form.is_valid():
        grade = form.save(commit=False)
        grade.graded_by = user
        if not grade.graded_at:
            grade.graded_at = timezone.now()

        # Record history if changed
        if (old_score != grade.numeric_score or old_letter != grade.letter_grade) and not created:
            GradeHistory.objects.create(
                grade=grade,
                changed_by=user,
                old_numeric_score=old_score,
                new_numeric_score=grade.numeric_score,
                old_letter_grade=old_letter or '',
                new_letter_grade=grade.letter_grade or '',
                reason=request.POST.get('change_reason', ''),
            )

        grade.save()

        # Update student GPA if finalized
        if grade.is_finalized:
            enrollment.student.update_gpa()

        messages.success(
            request,
            f'Grade saved for {enrollment.student.user.get_full_name()}.'
        )
        return redirect('grades:course_grades', course_pk=enrollment.course.pk)

    return render(request, 'grades/grade_entry.html', {
        'form': form,
        'enrollment': enrollment,
        'grade': grade,
        'course': enrollment.course,
    })


# ---------------------------------------------------------------------------
# Bulk Grade Entry — all students in a course
# ---------------------------------------------------------------------------
@professor_required
def bulk_grade_entry_view(request, course_pk):
    """Enter grades for all enrolled students in a course at once."""
    course = get_object_or_404(Course, pk=course_pk)
    user = request.user

    if user.is_professor and course.professor != user:
        messages.error(request, 'You can only grade your own courses.')
        return redirect('grades:list')

    enrollments = Enrollment.objects.filter(
        course=course, status='enrolled'
    ).select_related('student__user').order_by('student__student_id')

    form = BulkGradeEntryForm(request.POST or None, enrollments=enrollments)

    if request.method == 'POST' and form.is_valid():
        saved = 0
        for enrollment in enrollments:
            data = form.get_grade_data(enrollment)
            if data['numeric_score'] is not None or data['letter_grade']:
                grade, _ = Grade.objects.get_or_create(
                    enrollment=enrollment,
                    defaults={'graded_by': user}
                )
                if data['numeric_score'] is not None:
                    grade.numeric_score = data['numeric_score']
                if data['letter_grade']:
                    grade.letter_grade = data['letter_grade']
                    grade.grade_points = Grade.GPA_POINTS.get(
                        data['letter_grade'], 0.00
                    )
                if data['remarks']:
                    grade.remarks = data['remarks']
                grade.graded_by = user
                grade.graded_at = timezone.now()
                grade.compute_grade()
                grade.save()
                saved += 1

        messages.success(request, f'Grades saved for {saved} student(s).')
        return redirect('courses:detail', pk=course.pk)

    # Annotate each enrollment with existing grade
    enrollment_grade_pairs = []
    for enrollment in enrollments:
        existing = Grade.objects.filter(enrollment=enrollment).first()
        enrollment_grade_pairs.append((enrollment, existing))

    return render(request, 'grades/bulk_grade_entry.html', {
        'course': course,
        'form': form,
        'enrollment_grade_pairs': enrollment_grade_pairs,
    })


# ---------------------------------------------------------------------------
# Course Grades Overview
# ---------------------------------------------------------------------------
@login_required
def course_grades_view(request, course_pk):
    """Grade overview for a specific course."""
    course = get_object_or_404(Course, pk=course_pk)
    user = request.user

    if user.is_professor and course.professor != user:
        messages.error(request, 'Permission denied.')
        return redirect('courses:list')

    enrollments = Enrollment.objects.filter(
        course=course, status='enrolled'
    ).select_related('student__user').prefetch_related('grade')

    # Grade distribution
    grades = Grade.objects.filter(enrollment__course=course)
    distribution = {}
    for g in grades:
        if g.letter_grade:
            first = g.letter_grade[0] if g.letter_grade[0] in 'ABCDF' else g.letter_grade
            distribution[first] = distribution.get(first, 0) + 1

    avg_score = grades.filter(
        numeric_score__isnull=False
    ).aggregate(avg=Avg('numeric_score'))['avg']

    return render(request, 'grades/course_grades.html', {
        'course': course,
        'enrollments': enrollments,
        'distribution': distribution,
        'avg_score': round(avg_score, 2) if avg_score else None,
        'total_enrolled': enrollments.count(),
        'graded_count': grades.count(),
        'finalized_count': grades.filter(is_finalized=True).count(),
    })


# ---------------------------------------------------------------------------
# Student Grade Report (student's own grades)
# ---------------------------------------------------------------------------
@login_required
def student_grade_report_view(request):
    """Student views all their own grades across all courses."""
    if not request.user.is_student:
        messages.error(request, 'Students only.')
        return redirect('core:dashboard')

    try:
        student = request.user.student_profile
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('core:dashboard')

    grades = Grade.objects.filter(
        enrollment__student=student
    ).select_related(
        'enrollment__course', 'enrollment__course__professor'
    ).order_by('-enrollment__course__academic_year', 'enrollment__course__semester')

    # GPA calculation
    finalized = grades.filter(is_finalized=True)
    gpa = 0.0
    if finalized.exists():
        gpa = round(
            sum(float(g.grade_points) for g in finalized) / finalized.count(), 2
        )

    return render(request, 'grades/student_grade_report.html', {
        'student': student,
        'grades': grades,
        'gpa': gpa,
        'finalized_count': finalized.count(),
        'pending_count': grades.filter(is_finalized=False).count(),
    })


# ---------------------------------------------------------------------------
# Finalize Grade
# ---------------------------------------------------------------------------
@professor_required
def finalize_grade_view(request, pk):
    """Finalize a grade (locks it from student-visible editing)."""
    grade = get_object_or_404(Grade, pk=pk)
    user = request.user

    if user.is_professor and grade.enrollment.course.professor != user:
        messages.error(request, 'Permission denied.')
        return redirect('grades:list')

    if request.method == 'POST':
        if not grade.numeric_score and not grade.letter_grade:
            messages.error(request, 'Cannot finalize a grade with no score entered.')
            return redirect('grades:entry', enrollment_pk=grade.enrollment.pk)

        grade.is_finalized = True
        grade.finalized_at = timezone.now()
        grade.graded_by = user
        grade.save()
        grade.enrollment.student.update_gpa()
        messages.success(
            request,
            f'Grade finalized for {grade.enrollment.student.user.get_full_name()}.'
        )
        return redirect(
            'grades:course_grades',
            course_pk=grade.enrollment.course.pk
        )

    return render(request, 'grades/finalize_confirm.html', {'grade': grade})


# ---------------------------------------------------------------------------
# Grade Components
# ---------------------------------------------------------------------------
@professor_required
def manage_grade_components_view(request, course_pk):
    """Manage grading breakdown for a course."""
    course = get_object_or_404(Course, pk=course_pk)
    user = request.user

    if user.is_professor and course.professor != user:
        messages.error(request, 'Permission denied.')
        return redirect('courses:list')

    formset = GradeComponentFormSet(
        request.POST or None,
        queryset=GradeComponent.objects.filter(course=course).order_by('order')
    )

    if request.method == 'POST' and formset.is_valid():
        components = formset.save(commit=False)
        for comp in components:
            comp.course = course
            comp.save()
        for deleted in formset.deleted_objects:
            deleted.delete()

        # Validate total weight = 100
        total = sum(
            float(c.weight)
            for c in GradeComponent.objects.filter(course=course)
        )
        if total != 100.0:
            messages.warning(
                request,
                f'Warning: Component weights total {total}% (should be 100%).'
            )
        else:
            messages.success(request, 'Grade components saved successfully.')
        return redirect('courses:detail', pk=course.pk)

    return render(request, 'grades/grade_components.html', {
        'course': course,
        'formset': formset,
    })


# ---------------------------------------------------------------------------
# Admin: Grade Override
# ---------------------------------------------------------------------------
@admin_required
def admin_grade_override_view(request, pk):
    """Admin can override any finalized grade."""
    grade = get_object_or_404(Grade, pk=pk)
    old_score = grade.numeric_score
    old_letter = grade.letter_grade

    form = GradeForm(request.POST or None, instance=grade)
    if request.method == 'POST' and form.is_valid():
        # Log override history
        GradeHistory.objects.create(
            grade=grade,
            changed_by=request.user,
            old_numeric_score=old_score,
            new_numeric_score=form.cleaned_data.get('numeric_score'),
            old_letter_grade=old_letter or '',
            new_letter_grade=form.cleaned_data.get('letter_grade', ''),
            reason=f'[ADMIN OVERRIDE] {request.POST.get("change_reason", "")}',
        )
        grade = form.save()
        grade.enrollment.student.update_gpa()
        messages.success(request, 'Grade overridden successfully.')
        return redirect('grades:detail', pk=grade.pk)

    return render(request, 'grades/admin_grade_override.html', {
        'form': form,
        'grade': grade,
    })