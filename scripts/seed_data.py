"""
scripts/seed_data.py

Seed data script — works with the corrected settings.py and apps.py files.
Automatically adds project root to sys.path so it works when run directly.

Usage:
    python scripts/seed_data.py
"""

import os
import sys

# ── Step 1: Add project root to path ────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── Step 2: Set Django settings BEFORE any other import ─────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_system.settings')

# ── Step 3: Setup Django ─────────────────────────────────────────
import django
django.setup()

# ── Step 4: Now import everything ───────────────────────────────
import random
from datetime import date, timedelta, time
from decimal import Decimal

from django.utils import timezone
from django.db import transaction, connection

from apps.accounts.models import User, UserRole, Department, StudentProfile, ProfessorProfile
from apps.courses.models import Course, Enrollment, Announcement
from apps.grades.models import Grade, GradeComponent, GradeHistory
from apps.attendance.models import AttendanceSession, AttendanceRecord, AttendanceSummary
from apps.assignments.models import Assignment, AssignmentSubmission, SubmissionComment


# ── Helpers ──────────────────────────────────────────────────────
def log(msg):
    print(f"  [OK]  {msg}")

def err(msg):
    print(f"  [!!]  {msg}")

def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


# ── Pre-flight check ─────────────────────────────────────────────
def check_tables():
    """Verify all required tables exist before seeding."""
    required = [
        'auth_user', 'accounts_department',
        'student_profiles', 'professor_profiles',
        'courses', 'enrollments', 'announcements',
        'grades', 'grade_components',
        'attendance_sessions', 'attendance_records', 'attendance_summaries',
        'assignments', 'assignment_submissions', 'submission_comments',
    ]
    existing = connection.introspection.table_names()
    missing = [t for t in required if t not in existing]
    if missing:
        print("\n[ERROR] The following tables do not exist:")
        for t in missing:
            print(f"  - {t}")
        print("\nYou must run migrations first:")
        print("  python manage.py makemigrations accounts")
        print("  python manage.py makemigrations courses")
        print("  python manage.py makemigrations grades")
        print("  python manage.py makemigrations attendance")
        print("  python manage.py makemigrations assignments")
        print("  python manage.py migrate")
        print("\nOr simply run: python setup.py")
        sys.exit(1)
    log(f"All {len(required)} required tables found.")


# ════════════════════════════════════════════════════════════════
# MAIN SEED FUNCTION
# ════════════════════════════════════════════════════════════════
@transaction.atomic
def seed():
    print("\n" + "="*55)
    print("  Academic Management System — Seed Data")
    print("="*55)

    # ── Pre-flight ───────────────────────────────────────────────
    section("Checking database tables")
    check_tables()

    # ── 1. Clear existing data ───────────────────────────────────
    section("Clearing existing data")
    for model in [
        SubmissionComment, AssignmentSubmission, Assignment,
        AttendanceSummary, AttendanceRecord, AttendanceSession,
        GradeHistory, GradeComponent, Grade,
        Announcement, Enrollment, Course,
        StudentProfile, ProfessorProfile,
        Department,
    ]:
        count = model.objects.count()
        model.objects.all().delete()
        log(f"Cleared {count} {model.__name__}")

    deleted, _ = User.objects.filter(is_superuser=False).delete()
    log(f"Cleared {deleted} non-superuser User records")

    # ── 2. Departments ───────────────────────────────────────────
    section("Creating Departments")
    dept_data = [
        ("Computer Science",   "CS",   "Computation, algorithms, and software systems."),
        ("Mathematics",        "MATH", "Pure and applied mathematics including statistics."),
        ("Physics",            "PHY",  "Fundamental laws of nature and the universe."),
        ("English Literature", "ENG",  "Language, writing, and literary studies."),
        ("Business Admin",     "BUS",  "Management, finance, and organisational behaviour."),
        ("Engineering",        "ENG2", "Applied engineering disciplines."),
    ]
    departments = {}
    for name, code, desc in dept_data:
        d = Department.objects.create(name=name, code=code, description=desc)
        departments[code] = d
        log(f"Department: {code} — {name}")

    # ── 3. Admin ─────────────────────────────────────────────────
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
    prof_data = [
        ("alice.johnson", "Alice", "Johnson", "CS",   "full",      "Artificial Intelligence & ML"),
        ("bob.smith",     "Bob",   "Smith",   "MATH", "associate", "Calculus & Linear Algebra"),
        ("carol.white",   "Carol", "White",   "PHY",  "assistant", "Quantum Mechanics"),
        ("david.brown",   "David", "Brown",   "ENG",  "lecturer",  "Creative Writing & Literature"),
        ("eve.davis",     "Eve",   "Davis",   "BUS",  "associate", "Financial Management"),
        ("frank.miller",  "Frank", "Miller",  "CS",   "assistant", "Web Development & Databases"),
        ("grace.wilson",  "Grace", "Wilson",  "ENG2", "full",      "Structural Engineering"),
    ]
    professors = []
    for i, (uname, first, last, dept, rank, spec) in enumerate(prof_data, 1):
        u = User.objects.create_user(
            email=f"{uname}@ams.edu",
            password="Prof@1234",
            first_name=first,
            last_name=last,
            role=UserRole.PROFESSOR,
            phone=f"+1555{i:07d}",
            bio=f"Professor {first} {last} specializes in {spec}.",
        )
        p = ProfessorProfile.objects.create(
            user=u,
            employee_id=f"EMP-{2020 + i}-{i:03d}",
            department=departments[dept],
            rank=rank,
            specialization=spec,
            office_location=f"Building {chr(64 + i)}, Room {100 + i * 10}",
            office_hours="Mon/Wed 2–4 PM, Fri 10 AM–12 PM",
            hire_date=date(2018 + i % 5, i % 12 + 1, 1),
        )
        professors.append((u, p))
        log(f"Professor: {u.email} / Prof@1234  [{dept}]")

    departments["CS"].head = professors[0][0]
    departments["CS"].save()
    departments["MATH"].head = professors[1][0]
    departments["MATH"].save()

    # ── 5. Students ──────────────────────────────────────────────
    section("Creating 40 Students")
    first_names = [
        "James","Mary","John","Patricia","Robert","Jennifer","Michael","Linda",
        "William","Barbara","David","Susan","Richard","Jessica","Joseph","Sarah",
        "Thomas","Karen","Charles","Lisa","Christopher","Nancy","Daniel","Betty",
        "Matthew","Margaret","Anthony","Sandra","Mark","Ashley","Donald","Emily",
        "Steven","Kimberly","Paul","Donna","Andrew","Carol","Joshua","Ruth",
    ]
    last_names = [
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
            first = random.choice(first_names)
            last = random.choice(last_names)
            if (first, last) not in used_names:
                used_names.add((first, last))
                break
        yr = random.randint(1, 4)
        dept_code = random.choice(["CS", "MATH", "PHY", "ENG", "BUS", "ENG2"])
        u = User.objects.create_user(
            email=f"{first.lower()}.{last.lower()}{i:02d}@student.ams.edu",
            password="Student@1234",
            first_name=first,
            last_name=last,
            role=UserRole.STUDENT,
            phone=f"+1444{i:07d}",
            date_of_birth=date(
                2000 + random.randint(0, 5),
                random.randint(1, 12),
                random.randint(1, 28),
            ),
        )
        p = StudentProfile.objects.create(
            user=u,
            student_id=f"STU-2024-{i:04d}",
            department=departments[dept_code],
            year_of_study=yr,
            enrollment_date=date(2024 - yr + 1, 8, 15),
            expected_graduation=date(2024 - yr + 5, 5, 15),
            status="active",
            scholarship=random.random() < 0.15,
            emergency_contact_name=f"Parent of {first}",
            emergency_contact_phone=f"+1333{i:07d}",
        )
        students.append((u, p))
    log(f"Created {len(students)} students  [password: Student@1234]")

    # ── 6. Courses ───────────────────────────────────────────────
    section("Creating Courses")
    course_data = [
        ("CS101",   "Introduction to Computer Science",   0, "CS",   3, 35, "Mon,Wed,Fri", time(9,0),  time(9,50),  "CS-101",  "in_person"),
        ("CS201",   "Data Structures & Algorithms",        0, "CS",   3, 30, "Tue,Thu",     time(10,0), time(11,30), "CS-201",  "in_person"),
        ("CS301",   "Database Systems",                    5, "CS",   3, 28, "Mon,Wed",     time(14,0), time(15,30), "CS-102",  "in_person"),
        ("CS401",   "Machine Learning",                    0, "CS",   3, 25, "Mon,Wed,Fri", time(13,0), time(13,50), "CS-301",  "hybrid"),
        ("MATH101", "Calculus I",                          1, "MATH", 4, 40, "Mon,Wed,Fri", time(8,0),  time(8,50),  "M-101",   "in_person"),
        ("MATH201", "Linear Algebra",                      1, "MATH", 3, 30, "Tue,Thu",     time(13,0), time(14,30), "M-201",   "in_person"),
        ("MATH301", "Probability & Statistics",             1, "MATH", 3, 35, "Mon,Wed",     time(10,0), time(11,30), "M-301",   "in_person"),
        ("PHY101",  "Physics I: Mechanics",                2, "PHY",  4, 38, "Mon,Wed,Fri", time(11,0), time(11,50), "P-101",   "in_person"),
        ("ENG101",  "English Composition",                 3, "ENG",  3, 30, "Tue,Thu",     time(9,0),  time(10,30), "E-101",   "in_person"),
        ("ENG201",  "World Literature",                    3, "ENG",  3, 25, "Mon,Wed,Fri", time(15,0), time(15,50), "E-201",   "in_person"),
        ("BUS101",  "Principles of Business",              4, "BUS",  3, 45, "Tue,Thu",     time(11,0), time(12,30), "B-101",   "in_person"),
        ("BUS301",  "Financial Accounting",                4, "BUS",  3, 30, "Mon,Wed,Fri", time(10,0), time(10,50), "B-201",   "hybrid"),
        ("CS501",   "Advanced Web Development",            5, "CS",   3, 20, "Tue,Thu",     time(14,0), time(15,30), "CS-Lab",  "in_person"),
        ("ENG301",  "Creative Writing",                    3, "ENG",  3, 20, "Mon,Wed",     time(13,0), time(14,30), "E-301",   "in_person"),
        ("PHY201",  "Physics II: Electromagnetism",        2, "PHY",  4, 32, "Mon,Wed,Fri", time(9,0),  time(9,50),  "P-201",   "in_person"),
    ]
    courses = []
    for code, title, pi, dc, cr, mx, days, st, et, room, mode in course_data:
        c = Course.objects.create(
            course_code=code,
            title=title,
            description=(
                f"This course covers key concepts in {title.lower()}. "
                "Students will gain solid understanding through lectures, "
                "assignments, and hands-on projects."
            ),
            professor=professors[pi][0],
            department=departments[dc],
            academic_year="2025-2026",
            semester="Spring",
            credits=cr,
            max_students=mx,
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
        courses.append(c)
        log(f"Course: {code} — {title[:40]}")

    # ── 7. Grade Components ──────────────────────────────────────
    section("Creating Grade Components")
    for course in courses:
        for nm, ct, w, ms, o in [
            ("Midterm Exam",  "midterm",       30, 100, 1),
            ("Final Exam",    "final",         40, 100, 2),
            ("Assignments",   "assignment",    20, 100, 3),
            ("Participation", "participation", 10, 100, 4),
        ]:
            GradeComponent.objects.create(
                course=course, name=nm, component_type=ct,
                weight=w, max_score=ms, order=o,
            )
    log(f"Created {len(courses) * 4} grade components")

    # ── 8. Enrollments ───────────────────────────────────────────
    section("Creating Enrollments")
    enrollment_count = 0
    student_enrollments = {sp.pk: [] for _, sp in students}

    for _, sp in students:
        chosen = random.sample(courses, min(random.randint(3, 5), len(courses)))
        for course in chosen:
            if course.enrolled_count >= course.max_students:
                continue
            e = Enrollment.objects.create(
                student=sp,
                course=course,
                status="enrolled",
                enrollment_date=timezone.now() - timedelta(days=random.randint(30, 90)),
            )
            AttendanceSummary.objects.get_or_create(enrollment=e)
            student_enrollments[sp.pk].append(e)
            enrollment_count += 1
    log(f"Created {enrollment_count} enrollments")

    # ── 9. Announcements ─────────────────────────────────────────
    section("Creating Announcements")
    ann_templates = [
        ("Midterm Exam Schedule",      "exam",       "high",   "Your midterm is next week. Review chapters 1-6 and bring your student ID."),
        ("Assignment Due Date",        "assignment", "normal", "Assignment 2 is due this Friday at 11:59 PM. Late submissions incur a 10% penalty."),
        ("Office Hours Update",        "general",    "normal", "Office hours this week: Wednesday 3-5 PM. Plan accordingly."),
        ("Course Material Updated",    "general",    "normal", "New slides for week 8 uploaded. Review before next class."),
        ("Guest Lecture Announcement", "general",    "high",   "Guest lecturer joining us next Tuesday. Attendance mandatory."),
        ("Final Exam Information",     "exam",       "urgent", "Final exam covers all semester material. Study guide posted end of week."),
        ("Grade Release",              "grade",      "normal", "Midterm grades released. Check your report and contact me with questions."),
    ]
    ann_count = 0
    for course in courses:
        chosen = random.sample(ann_templates, min(random.randint(2, 5), len(ann_templates)))
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
    assign_templates = [
        ("Homework 1: Fundamentals",     "homework", 100, 20, -20, "published"),
        ("Homework 2: Applied Concepts", "homework", 100, 15, -10, "published"),
        ("Midterm Project",              "project",  150, 10,   5, "published"),
        ("Quiz 1",                       "quiz",      50, 25,  -5, "published"),
        ("Quiz 2",                       "quiz",      50, 12,   3, "published"),
        ("Final Project",                "project",  200,  5,  30, "published"),
        ("Lab Report 1",                 "lab",      100, 30,  -3, "published"),
        ("Essay: Critical Analysis",     "essay",    100, 20,   7, "published"),
        ("Homework 3: Advanced Topics",  "homework", 100,  3,  14, "draft"),
    ]
    all_assignments = []
    for course in courses:
        chosen = random.sample(assign_templates, min(random.randint(4, 7), len(assign_templates)))
        for title, atype, max_score, days_ago, days_delta, status in chosen:
            a = Assignment.objects.create(
                course=course,
                created_by=course.professor,
                title=f"{title} — {course.course_code}",
                description=(
                    f"Complete all required tasks for {title.lower()}. "
                    "Submit via the course portal by the due date. "
                    "Follow submission guidelines in the syllabus."
                ),
                assignment_type=atype,
                status=status,
                max_score=Decimal(str(max_score)),
                weight=Decimal(str(random.choice([5, 10, 15, 20]))),
                assigned_date=timezone.now() - timedelta(days=days_ago),
                due_date=timezone.now() + timedelta(days=days_delta),
                late_submission_allowed=random.random() < 0.4,
                late_penalty_percent=Decimal("10.00"),
                allow_resubmission=random.random() < 0.2,
                submission_format="PDF, DOCX",
            )
            all_assignments.append(a)
    log(f"Created {len(all_assignments)} assignments")

    # ── 11. Submissions ──────────────────────────────────────────
    section("Creating Submissions")
    sub_count = 0
    graded_count = 0
    for _, sp in students:
        for e in student_enrollments[sp.pk]:
            course_assignments = [
                a for a in all_assignments
                if a.course_id == e.course_id and a.status == "published"
            ]
            for a in course_assignments:
                if random.random() < 0.25:
                    continue
                is_late = a.due_date < timezone.now() and random.random() < 0.1
                submitted_at = min(
                    a.due_date + timedelta(hours=random.randint(1, 24)) if is_late
                    else a.due_date - timedelta(days=random.randint(1, 5)),
                    timezone.now(),
                )
                score = None
                is_graded = False
                if a.due_date < timezone.now() and random.random() < 0.85:
                    score = Decimal(str(round(random.uniform(55, 100), 2)))
                    is_graded = True
                    graded_count += 1
                AssignmentSubmission.objects.create(
                    assignment=a,
                    student=sp,
                    submission_text=(
                        f"This is my submission for {a.title}. "
                        "I have completed all required sections as outlined "
                        "in the assignment description."
                    ),
                    status="graded" if is_graded else ("late" if is_late else "submitted"),
                    submitted_at=submitted_at,
                    is_late=is_late,
                    score=score,
                    adjusted_score=score,
                    is_graded=is_graded,
                    graded_by=a.course.professor if is_graded else None,
                    graded_at=(
                        timezone.now() - timedelta(days=random.randint(0, 5))
                        if is_graded else None
                    ),
                    feedback=f"Good work. Score: {score}/{a.max_score}." if is_graded else "",
                )
                sub_count += 1
    log(f"Created {sub_count} submissions ({graded_count} graded)")

    # ── 12. Attendance ───────────────────────────────────────────
    section("Creating Attendance Sessions & Records")
    session_count = 0
    record_count = 0
    topics = [
        "Introduction & Overview", "Core Concepts Part 1", "Core Concepts Part 2",
        "Deep Dive: Theory", "Lab Session", "Workshop", "Guest Speaker",
        "Review Session", "Case Study", "Problem Solving", "Presentations", "Exam Review",
    ]
    for course in courses:
        n = random.randint(8, 12)
        session_dates = sorted({
            date.today() - timedelta(days=random.randint(5, 90))
            for _ in range(n)
        })
        for i, sd in enumerate(session_dates):
            sess = AttendanceSession.objects.create(
                course=course,
                date=sd,
                session_type="lecture",
                topic=topics[i % len(topics)],
                created_by=course.professor,
                is_locked=(i < len(session_dates) - 2),
            )
            session_count += 1
            for e in Enrollment.objects.filter(course=course, status="enrolled"):
                r = random.random()
                if r < 0.78:       status = "present"
                elif r < 0.88:     status = "absent"
                elif r < 0.93:     status = "late"
                elif r < 0.97:     status = "excused"
                else:              status = "remote"
                AttendanceRecord.objects.create(
                    session=sess,
                    enrollment=e,
                    status=status,
                    excuse_reason="Medical appointment" if status == "excused" else "",
                    marked_by=course.professor,
                )
                record_count += 1
    log(f"Created {session_count} sessions, {record_count} attendance records")

    # Refresh summaries
    for summary in AttendanceSummary.objects.all():
        summary.refresh()
    log("Refreshed all attendance summaries")

    # ── 13. Grades ───────────────────────────────────────────────
    section("Creating Grades")
    grade_count = 0
    finalized_count = 0
    for _, sp in students:
        for e in student_enrollments[sp.pk]:
            if random.random() < 0.2:
                continue
            num = max(Decimal("45"), min(Decimal("100"),
                      Decimal(str(round(random.gauss(76, 12), 2)))))
            letter = Grade.score_to_letter(num)
            gp = Decimal(str(Grade.GPA_POINTS.get(letter, 0.00)))
            is_final = random.random() < 0.65
            mid = max(Decimal("0"), min(Decimal("100"),
                  Decimal(str(round(float(num) * random.uniform(0.85, 1.15), 2)))))
            fin = max(Decimal("0"), min(Decimal("100"),
                  Decimal(str(round(float(num) * random.uniform(0.85, 1.15), 2)))))
            Grade.objects.create(
                enrollment=e,
                graded_by=e.course.professor,
                numeric_score=num,
                letter_grade=letter,
                grade_points=gp,
                midterm_score=mid,
                final_score=fin,
                assignment_score=Decimal(str(round(random.uniform(60, 100), 2))),
                quiz_score=Decimal(str(round(random.uniform(60, 100), 2))),
                participation_score=Decimal(str(round(random.uniform(70, 100), 2))),
                is_finalized=is_final,
                remarks=random.choice([
                    "Excellent performance throughout the semester.",
                    "Good understanding of the material.",
                    "Satisfactory work; room for improvement.",
                    "Needs to engage more actively in class discussions.",
                    "Strong analytical skills demonstrated.",
                ]),
                graded_at=timezone.now() - timedelta(days=random.randint(1, 30)),
                finalized_at=(
                    timezone.now() - timedelta(days=random.randint(0, 10))
                    if is_final else None
                ),
            )
            grade_count += 1
            if is_final:
                finalized_count += 1
    log(f"Created {grade_count} grades ({finalized_count} finalized)")

    # ── 14. Update GPAs ──────────────────────────────────────────
    section("Updating Student GPAs")
    for _, sp in students:
        sp.update_gpa()
    log(f"Updated GPA for {len(students)} students")

    # ── Summary ──────────────────────────────────────────────────
    print("\n" + "="*55)
    print("  SEED COMPLETE")
    print("="*55)
    print(f"  Departments:    {Department.objects.count()}")
    print(f"  Users:          1 admin + {len(professors)} professors + {len(students)} students")
    print(f"  Courses:        {Course.objects.count()}")
    print(f"  Enrollments:    {Enrollment.objects.count()}")
    print(f"  Assignments:    {Assignment.objects.count()}")
    print(f"  Submissions:    {AssignmentSubmission.objects.count()}")
    print(f"  Att Sessions:   {AttendanceSession.objects.count()}")
    print(f"  Att Records:    {AttendanceRecord.objects.count()}")
    print(f"  Grades:         {Grade.objects.count()}")
    print(f"  Announcements:  {Announcement.objects.count()}")
    print()
    print("  ── Login Credentials ──────────────────────────────")
    print("  Admin:     admin@ams.edu            / Admin@1234")
    print("  Professor: alice.johnson@ams.edu    / Prof@1234")
    print("  Professor: bob.smith@ams.edu        / Prof@1234")
    print(f"  Student:   {students[0][0].email}")
    print("             password: Student@1234")
    print("="*55)
    print("\n  Run the server: python manage.py runserver")
    print("  Open:           http://127.0.0.1:8000")


# ── Entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    seed()
else:
    seed()