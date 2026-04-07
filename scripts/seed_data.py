"""
scripts/seed_data.py

Complete seed data script for the Academic Management System.
Creates realistic sample data for all models.

Usage:
    python manage.py shell < scripts/seed_data.py
  OR
    python manage.py runscript seed_data   (requires django-extensions)

WARNING: Clears all existing data before seeding.
         Do NOT run on production.
"""

import os
import sys
import django
import random
from datetime import date, timedelta, time
from decimal import Decimal

# ── Bootstrap Django ────────────────────────────────────────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_system.settings')
django.setup()

from django.utils import timezone
from django.db import transaction

from apps.accounts.models import User, UserRole, Department, StudentProfile, ProfessorProfile
from apps.courses.models import Course, Enrollment, Announcement
from apps.grades.models import Grade, GradeComponent, GradeHistory
from apps.attendance.models import AttendanceSession, AttendanceRecord, AttendanceSummary
from apps.assignments.models import Assignment, AssignmentSubmission, SubmissionComment


# ── Helpers ──────────────────────────────────────────────────────
def log(msg):
    print(f"  ✓  {msg}")

def warn(msg):
    print(f"  ⚠  {msg}")

def section(title):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}")

def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))

def past_datetime(days_ago_max=60, days_ago_min=1):
    days = random.randint(days_ago_min, days_ago_max)
    return timezone.now() - timedelta(days=days, hours=random.randint(0, 8))

def future_datetime(days_ahead_min=3, days_ahead_max=30):
    days = random.randint(days_ahead_min, days_ahead_max)
    return timezone.now() + timedelta(days=days, hours=random.randint(0, 8))


# ════════════════════════════════════════════════════════════════
# MAIN SEED FUNCTION
# ════════════════════════════════════════════════════════════════
@transaction.atomic
def seed():
    print("\n" + "═"*50)
    print("  Academic Management System — Seed Data")
    print("═"*50)

    # ── 1. Clear existing data ───────────────────────────────────
    section("Clearing existing data")
    models_to_clear = [
        SubmissionComment, AssignmentSubmission, Assignment,
        AttendanceSummary, AttendanceRecord, AttendanceSession,
        GradeHistory, GradeComponent, Grade,
        Announcement, Enrollment, Course,
        StudentProfile, ProfessorProfile,
        Department,
    ]
    for model in models_to_clear:
        count = model.objects.count()
        model.objects.all().delete()
        log(f"Cleared {count} {model.__name__} records")

    # Clear non-superuser users
    deleted, _ = User.objects.filter(is_superuser=False).delete()
    log(f"Cleared {deleted} User records")

    # ── 2. Departments ───────────────────────────────────────────
    section("Creating Departments")
    dept_data = [
        ("Computer Science",   "CS",   "Study of computation, algorithms, and software systems."),
        ("Mathematics",        "MATH", "Pure and applied mathematics including statistics."),
        ("Physics",            "PHY",  "Fundamental laws of nature and the universe."),
        ("English Literature", "ENG",  "Language, writing, and literary studies."),
        ("Business Admin",     "BUS",  "Management, finance, and organizational behaviour."),
        ("Engineering",        "ENG2", "Applied engineering disciplines."),
    ]
    departments = {}
    for name, code, desc in dept_data:
        dept = Department.objects.create(name=name, code=code, description=desc)
        departments[code] = dept
        log(f"Department: {code} — {name}")

    # ── 3. Admin User ────────────────────────────────────────────
    section("Creating Admin User")
    admin = User.objects.create_superuser(
        email="admin@ams.edu",
        password="Admin@1234",
        first_name="System",
        last_name="Administrator",
        role=UserRole.ADMIN,
    )
    log(f"Admin: {admin.email} / Admin@1234")

    # ── 4. Professors ────────────────────────────────────────────
    section("Creating Professors")
    professor_data = [
        ("alice.johnson",  "Alice",   "Johnson",  "CS",   "full",      "Artificial Intelligence & ML"),
        ("bob.smith",      "Bob",     "Smith",    "MATH", "associate", "Calculus & Linear Algebra"),
        ("carol.white",    "Carol",   "White",    "PHY",  "assistant", "Quantum Mechanics"),
        ("david.brown",    "David",   "Brown",    "ENG",  "lecturer",  "Creative Writing & Literature"),
        ("eve.davis",      "Eve",     "Davis",    "BUS",  "associate", "Financial Management"),
        ("frank.miller",   "Frank",   "Miller",   "CS",   "assistant", "Web Development & Databases"),
        ("grace.wilson",   "Grace",   "Wilson",   "ENG2", "full",      "Structural Engineering"),
    ]
    professors = []
    for i, (username, first, last, dept_code, rank, spec) in enumerate(professor_data, 1):
        user = User.objects.create_user(
            email=f"{username}@ams.edu",
            password="Prof@1234",
            first_name=first,
            last_name=last,
            role=UserRole.PROFESSOR,
            phone=f"+1555{i:07d}",
            bio=f"Professor {first} {last} specializes in {spec}.",
        )
        profile = ProfessorProfile.objects.create(
            user=user,
            employee_id=f"EMP-{2020+i:4d}-{i:03d}",
            department=departments[dept_code],
            rank=rank,
            specialization=spec,
            office_location=f"Building {chr(64+i)}, Room {100+i*10}",
            office_hours="Mon/Wed 2–4 PM, Fri 10 AM–12 PM",
            hire_date=date(2018 + i % 5, i % 12 + 1, 1),
        )
        professors.append((user, profile))
        log(f"Professor: {user.email} / Prof@1234  [{dept_code}]")

    # Update dept heads
    departments["CS"].head   = professors[0][0]
    departments["MATH"].head = professors[1][0]
    departments["CS"].save()
    departments["MATH"].save()

    # ── 5. Students ──────────────────────────────────────────────
    section("Creating Students")
    student_first = [
        "James","Mary","John","Patricia","Robert","Jennifer","Michael","Linda",
        "William","Barbara","David","Susan","Richard","Jessica","Joseph","Sarah",
        "Thomas","Karen","Charles","Lisa","Christopher","Nancy","Daniel","Betty",
        "Matthew","Margaret","Anthony","Sandra","Mark","Ashley","Donald","Emily",
        "Steven","Kimberly","Paul","Donna","Andrew","Carol","Joshua","Ruth",
    ]
    student_last = [
        "Anderson","Thomas","Jackson","White","Harris","Martin","Garcia","Thompson",
        "Martinez","Robinson","Clark","Rodriguez","Lewis","Lee","Walker","Hall",
        "Allen","Young","Hernandez","King","Wright","Lopez","Hill","Scott",
        "Green","Adams","Baker","Gonzalez","Nelson","Carter","Mitchell","Perez",
        "Roberts","Turner","Phillips","Campbell","Parker","Evans","Edwards","Collins",
    ]

    students = []
    used_names = set()
    for i in range(1, 41):
        while True:
            first = random.choice(student_first)
            last  = random.choice(student_last)
            if (first, last) not in used_names:
                used_names.add((first, last))
                break

        email = f"{first.lower()}.{last.lower()}{i:02d}@student.ams.edu"
        year  = random.randint(1, 4)
        dept_code = random.choice(["CS", "MATH", "PHY", "ENG", "BUS", "ENG2"])

        user = User.objects.create_user(
            email=email,
            password="Student@1234",
            first_name=first,
            last_name=last,
            role=UserRole.STUDENT,
            phone=f"+1444{i:07d}",
            date_of_birth=date(2000 + random.randint(0, 5), random.randint(1, 12), random.randint(1, 28)),
        )
        profile = StudentProfile.objects.create(
            user=user,
            student_id=f"STU-2024-{i:04d}",
            department=departments[dept_code],
            year_of_study=year,
            enrollment_date=date(2024 - year + 1, 8, 15),
            expected_graduation=date(2024 - year + 5, 5, 15),
            status='active',
            scholarship=random.random() < 0.15,
            emergency_contact_name=f"Parent of {first}",
            emergency_contact_phone=f"+1333{i:07d}",
        )
        students.append((user, profile))

    log(f"Created {len(students)} students  [password: Student@1234]")

    # ── 6. Courses ───────────────────────────────────────────────
    section("Creating Courses")
    course_data = [
        # (code, title, prof_idx, dept, credits, max, days, start, end, room, mode)
        ("CS101",  "Introduction to Computer Science",     0, "CS",   3, 35, "Mon,Wed,Fri",   time(9,0),  time(9,50),  "CS-101", "in_person"),
        ("CS201",  "Data Structures & Algorithms",          0, "CS",   3, 30, "Tue,Thu",        time(10,0), time(11,30), "CS-201", "in_person"),
        ("CS301",  "Database Systems",                      5, "CS",   3, 28, "Mon,Wed",        time(14,0), time(15,30), "CS-102", "in_person"),
        ("CS401",  "Machine Learning",                      0, "CS",   3, 25, "Mon,Wed,Fri",   time(13,0), time(13,50), "CS-301", "hybrid"),
        ("MATH101","Calculus I",                            1, "MATH", 4, 40, "Mon,Wed,Fri",   time(8,0),  time(8,50),  "M-101",  "in_person"),
        ("MATH201","Linear Algebra",                        1, "MATH", 3, 30, "Tue,Thu",        time(13,0), time(14,30), "M-201",  "in_person"),
        ("MATH301","Probability & Statistics",              1, "MATH", 3, 35, "Mon,Wed",        time(10,0), time(11,30), "M-301",  "in_person"),
        ("PHY101", "Physics I: Mechanics",                  2, "PHY",  4, 38, "Mon,Wed,Fri",   time(11,0), time(11,50), "P-101",  "in_person"),
        ("ENG101", "English Composition",                   3, "ENG",  3, 30, "Tue,Thu",        time(9,0),  time(10,30), "E-101",  "in_person"),
        ("ENG201", "World Literature",                      3, "ENG",  3, 25, "Mon,Wed,Fri",   time(15,0), time(15,50), "E-201",  "in_person"),
        ("BUS101", "Principles of Business",                4, "BUS",  3, 45, "Tue,Thu",        time(11,0), time(12,30), "B-101",  "in_person"),
        ("BUS301", "Financial Accounting",                  4, "BUS",  3, 30, "Mon,Wed,Fri",   time(10,0), time(10,50), "B-201",  "hybrid"),
        ("CS501",  "Advanced Web Development",              5, "CS",   3, 20, "Tue,Thu",        time(14,0), time(15,30), "CS-Lab", "in_person"),
        ("ENG301", "Creative Writing",                      3, "ENG",  3, 20, "Mon,Wed",        time(13,0), time(14,30), "E-301",  "in_person"),
        ("PHY201", "Physics II: Electromagnetism",          2, "PHY",  4, 32, "Mon,Wed,Fri",   time(9,0),  time(9,50),  "P-201",  "in_person"),
    ]

    courses = []
    for code, title, prof_idx, dept_code, credits, max_s, days, st, et, room, mode in course_data:
        course = Course.objects.create(
            course_code=code,
            title=title,
            description=f"This course covers key concepts in {title.lower()}. "
                        f"Students will develop a solid understanding through lectures, "
                        f"assignments, and hands-on projects.",
            professor=professors[prof_idx][0],
            department=departments[dept_code],
            academic_year="2025-2026",
            semester="Spring",
            credits=credits,
            max_students=max_s,
            schedule_days=days,
            start_time=st,
            end_time=et,
            room=room,
            delivery_mode=mode,
            status="active",
            is_active=True,
            start_date=date(2026, 1, 13),
            end_date=date(2026, 5, 10),
        )
        courses.append(course)
        log(f"Course: {code} — {title[:35]}")

    # ── 7. Grade Components ──────────────────────────────────────
    section("Creating Grade Components")
    standard_components = [
        ("Midterm Exam",    "midterm",      30, 100, 1),
        ("Final Exam",      "final",        40, 100, 2),
        ("Assignments",     "assignment",   20, 100, 3),
        ("Participation",   "participation", 10, 100, 4),
    ]
    for course in courses:
        for name, ctype, weight, max_score, order in standard_components:
            GradeComponent.objects.create(
                course=course,
                name=name,
                component_type=ctype,
                weight=weight,
                max_score=max_score,
                order=order,
            )
    log(f"Created {len(courses) * 4} grade components")

    # ── 8. Enrollments ───────────────────────────────────────────
    section("Creating Enrollments")
    enrollment_count = 0
    student_enrollments = {s[1].pk: [] for s in students}

    # Each student enrolls in 3–5 courses
    for student_user, student_profile in students:
        n_courses = random.randint(3, 5)
        chosen = random.sample(courses, min(n_courses, len(courses)))
        for course in chosen:
            if course.enrolled_count >= course.max_students:
                continue
            enrollment = Enrollment.objects.create(
                student=student_profile,
                course=course,
                status='enrolled',
                enrollment_date=timezone.now() - timedelta(days=random.randint(30, 90)),
            )
            AttendanceSummary.objects.get_or_create(enrollment=enrollment)
            student_enrollments[student_profile.pk].append(enrollment)
            enrollment_count += 1

    log(f"Created {enrollment_count} enrollments")

    # ── 9. Announcements ─────────────────────────────────────────
    section("Creating Announcements")
    ann_count = 0
    announcement_templates = [
        ("Midterm Exam Schedule",      "exam",    "high",   "Your midterm exam is scheduled for next week. Please review all chapters 1–6 and bring your student ID."),
        ("Assignment 2 Due Date",      "assignment","normal","Reminder: Assignment 2 is due this Friday at 11:59 PM. Late submissions will incur a 10% penalty."),
        ("Office Hours Update",        "general", "normal", "My office hours this week will be Wednesday 3–5 PM instead of the usual time. Please plan accordingly."),
        ("Course Material Updated",    "general", "normal", "New lecture slides for week 8 have been uploaded to the course portal. Please review before next class."),
        ("Guest Lecture Announcement", "general", "high",   "We will have a guest lecturer joining us next Tuesday. Attendance is mandatory for all enrolled students."),
        ("Final Exam Information",     "exam",    "urgent", "The final exam will cover all material from the entire semester. A study guide will be posted by end of week."),
        ("Grade Release",              "grade",   "normal", "Midterm grades have been released. Please check your grade report and contact me with any questions."),
    ]

    for course in courses:
        n_ann = random.randint(2, 5)
        chosen = random.sample(announcement_templates, min(n_ann, len(announcement_templates)))
        for i, (title, atype, priority, content) in enumerate(chosen):
            Announcement.objects.create(
                course=course,
                author=course.professor,
                title=f"{title} — {course.course_code}",
                content=f"{content}\n\nBest regards,\n{course.professor.get_full_name()}",
                announcement_type=atype,
                priority=priority,
                is_pinned=(i == 0),
                publish_at=timezone.now() - timedelta(days=random.randint(1, 45)),
            )
            ann_count += 1

    log(f"Created {ann_count} announcements")

    # ── 10. Assignments ──────────────────────────────────────────
    section("Creating Assignments")
    assignment_templates = [
        ("Homework 1: Fundamentals",      "homework",     100, 20, -20, "published"),
        ("Homework 2: Applied Concepts",  "homework",     100, 15, -10, "published"),
        ("Midterm Project",               "project",      150, 10,   5, "published"),
        ("Quiz 1",                        "quiz",          50, 25,  -5, "published"),
        ("Quiz 2",                        "quiz",          50, 12,   3, "published"),
        ("Final Project",                 "project",      200,  5,  30, "published"),
        ("Lab Report 1",                  "lab",          100, 30,  -3, "published"),
        ("Essay: Critical Analysis",      "essay",        100, 20,   7, "published"),
        ("Homework 3: Advanced Topics",   "homework",     100,  3,  14, "draft"),
    ]

    all_assignments = []
    for course in courses:
        n_assign = random.randint(4, 7)
        chosen = random.sample(assignment_templates, min(n_assign, len(assignment_templates)))
        for title, atype, max_score, days_ago, days_delta, status in chosen:
            due_date = timezone.now() + timedelta(days=days_delta)
            assigned_date = timezone.now() - timedelta(days=days_ago)
            a = Assignment.objects.create(
                course=course,
                created_by=course.professor,
                title=f"{title} — {course.course_code}",
                description=f"Complete all required tasks for {title.lower()}. "
                            f"Submit via the course portal by the due date. "
                            f"Follow the submission guidelines in the syllabus.",
                assignment_type=atype,
                status=status,
                max_score=Decimal(str(max_score)),
                weight=Decimal(str(random.choice([5, 10, 15, 20]))),
                assigned_date=assigned_date,
                due_date=due_date,
                late_submission_allowed=random.random() < 0.4,
                late_penalty_percent=Decimal("10.00"),
                allow_resubmission=random.random() < 0.2,
                submission_format="PDF, DOCX",
            )
            all_assignments.append(a)

    log(f"Created {len(all_assignments)} assignments")

    # ── 11. Assignment Submissions ───────────────────────────────
    section("Creating Submissions")
    submission_count = 0
    graded_count = 0

    for student_user, student_profile in students:
        enrollments = student_enrollments[student_profile.pk]
        for enrollment in enrollments:
            course_assignments = [a for a in all_assignments
                                  if a.course_id == enrollment.course_id and a.status == 'published']
            # Submit 60–90% of assignments
            for assignment in course_assignments:
                if random.random() < 0.25:
                    continue  # didn't submit

                is_late = assignment.due_date < timezone.now() and random.random() < 0.1
                submitted_at = (
                    assignment.due_date + timedelta(hours=random.randint(1, 24))
                    if is_late else
                    assignment.due_date - timedelta(days=random.randint(1, 5),
                                                     hours=random.randint(0, 12))
                )
                submitted_at = min(submitted_at, timezone.now())

                score = None
                is_graded = False

                # Grade past-due assignments
                if assignment.due_date < timezone.now() and random.random() < 0.85:
                    raw = random.uniform(55, 100)
                    score = Decimal(str(round(raw, 2)))
                    is_graded = True
                    graded_count += 1

                sub = AssignmentSubmission.objects.create(
                    assignment=assignment,
                    student=student_profile,
                    submission_text=f"This is my submission for {assignment.title}. "
                                    f"I have completed all required sections as outlined "
                                    f"in the assignment description.",
                    status='graded' if is_graded else ('late' if is_late else 'submitted'),
                    submitted_at=submitted_at,
                    is_late=is_late,
                    score=score,
                    adjusted_score=score,
                    is_graded=is_graded,
                    graded_by=assignment.course.professor if is_graded else None,
                    graded_at=timezone.now() - timedelta(days=random.randint(0, 5)) if is_graded else None,
                    feedback=(
                        f"Good work overall. Your understanding of the core concepts is evident. "
                        f"Score: {score}/{ assignment.max_score}."
                        if is_graded else ""
                    ),
                )
                submission_count += 1

    log(f"Created {submission_count} submissions ({graded_count} graded)")

    # ── 12. Attendance Sessions & Records ────────────────────────
    section("Creating Attendance Sessions & Records")
    session_count = 0
    record_count = 0

    for course in courses:
        # Create 8–12 past sessions per course
        n_sessions = random.randint(8, 12)
        topics = [
            "Introduction & Overview", "Core Concepts Part 1", "Core Concepts Part 2",
            "Deep Dive: Theory", "Lab Session", "Workshop",
            "Guest Speaker", "Review Session", "Case Study",
            "Problem Solving", "Presentations", "Exam Review",
        ]
        session_dates = sorted(
            [date.today() - timedelta(days=random.randint(5, 90)) for _ in range(n_sessions)]
        )
        used_dates = set()

        for i, session_date in enumerate(session_dates):
            if session_date in used_dates:
                continue
            used_dates.add(session_date)

            session = AttendanceSession.objects.create(
                course=course,
                date=session_date,
                session_type='lecture',
                topic=topics[i % len(topics)],
                created_by=course.professor,
                is_locked=(i < n_sessions - 2),  # recent sessions unlocked
            )
            session_count += 1

            # Mark attendance for enrolled students
            enrollments = Enrollment.objects.filter(course=course, status='enrolled')
            for enrollment in enrollments:
                # Realistic attendance distribution
                rand = random.random()
                if rand < 0.78:
                    status = 'present'
                elif rand < 0.88:
                    status = 'absent'
                elif rand < 0.93:
                    status = 'late'
                elif rand < 0.97:
                    status = 'excused'
                else:
                    status = 'remote'

                AttendanceRecord.objects.create(
                    session=session,
                    enrollment=enrollment,
                    status=status,
                    excuse_reason="Medical appointment" if status == 'excused' else "",
                    marked_by=course.professor,
                )
                record_count += 1

    log(f"Created {session_count} sessions, {record_count} attendance records")

    # Refresh all attendance summaries
    for summary in AttendanceSummary.objects.all():
        summary.refresh()
    log("Refreshed all attendance summaries")

    # ── 13. Grades ───────────────────────────────────────────────
    section("Creating Grades")
    grade_count = 0
    finalized_count = 0

    for student_user, student_profile in students:
        for enrollment in student_enrollments[student_profile.pk]:
            # 80% chance of having a grade
            if random.random() < 0.2:
                continue

            numeric = Decimal(str(round(random.gauss(76, 12), 2)))
            numeric = max(Decimal("45"), min(Decimal("100"), numeric))
            letter  = Grade.score_to_letter(numeric)
            gp      = Decimal(str(Grade.GPA_POINTS.get(letter, 0.00)))
            is_final = random.random() < 0.65

            midterm = Decimal(str(round(float(numeric) * random.uniform(0.85, 1.15), 2)))
            midterm = max(Decimal("0"), min(Decimal("100"), midterm))
            final_s = Decimal(str(round(float(numeric) * random.uniform(0.85, 1.15), 2)))
            final_s = max(Decimal("0"), min(Decimal("100"), final_s))

            grade = Grade.objects.create(
                enrollment=enrollment,
                graded_by=enrollment.course.professor,
                numeric_score=numeric,
                letter_grade=letter,
                grade_points=gp,
                midterm_score=midterm,
                final_score=final_s,
                assignment_score=Decimal(str(round(random.uniform(60, 100), 2))),
                quiz_score=Decimal(str(round(random.uniform(60, 100), 2))),
                participation_score=Decimal(str(round(random.uniform(70, 100), 2))),
                is_finalized=is_final,
                remarks=(
                    random.choice([
                        "Excellent performance throughout the semester.",
                        "Good understanding of the material.",
                        "Satisfactory work; room for improvement.",
                        "Needs to engage more actively in class discussions.",
                        "Strong analytical skills demonstrated.",
                    ])
                ),
                graded_at=timezone.now() - timedelta(days=random.randint(1, 30)),
                finalized_at=timezone.now() - timedelta(days=random.randint(0, 10)) if is_final else None,
            )
            grade_count += 1
            if is_final:
                finalized_count += 1

    log(f"Created {grade_count} grades ({finalized_count} finalized)")

    # ── 14. Update Student GPAs ──────────────────────────────────
    section("Recalculating Student GPAs")
    gpa_updated = 0
    for student_user, student_profile in students:
        student_profile.update_gpa()
        gpa_updated += 1
    log(f"Updated GPA for {gpa_updated} students")

    # ── 15. Summary ──────────────────────────────────────────────
    print("\n" + "═"*50)
    print("  SEED COMPLETE — Summary")
    print("═"*50)
    print(f"  Users:          1 admin + {len(professors)} professors + {len(students)} students")
    print(f"  Departments:    {Department.objects.count()}")
    print(f"  Courses:        {Course.objects.count()}")
    print(f"  Enrollments:    {Enrollment.objects.count()}")
    print(f"  Assignments:    {Assignment.objects.count()}")
    print(f"  Submissions:    {AssignmentSubmission.objects.count()}")
    print(f"  Att. Sessions:  {AttendanceSession.objects.count()}")
    print(f"  Att. Records:   {AttendanceRecord.objects.count()}")
    print(f"  Grades:         {Grade.objects.count()}")
    print(f"  Announcements:  {Announcement.objects.count()}")
    print()
    print("  ── Login Credentials ──────────────────────────")
    print("  Admin:     admin@ams.edu            / Admin@1234")
    print("  Professor: alice.johnson@ams.edu    / Prof@1234")
    print("  Professor: bob.smith@ams.edu        / Prof@1234")
    print("  Student:   (see first student email)/ Student@1234")
    print()

    # Print first student email for convenience
    first_student = students[0][0]
    print(f"  First Student: {first_student.email} / Student@1234")
    print("═"*50 + "\n")


# ── Entry point ──────────────────────────────────────────────────
if __name__ == '__main__':
    seed()
else:
    # When run via `python manage.py shell < scripts/seed_data.py`
    seed()