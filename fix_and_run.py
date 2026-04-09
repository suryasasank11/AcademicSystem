"""
fix_and_run.py  v7  —  FINAL with dynamic table name detection.

Changes from v6:
- Table verification uses model._meta.db_table (actual names from model)
  instead of hardcoded names. No more mismatch between what we check
  and what Django actually created.
- seed_data.py check_tables() also updated to use model-derived names.

Usage:
    python fix_and_run.py
"""
import os, sys, subprocess, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

G="\033[92m"; R="\033[91m"; Y="\033[93m"; BOLD="\033[1m"; E="\033[0m"

def ok(m):       print(f"  {G}[OK]{E}     {m}")
def err(m):      print(f"  {R}[ERROR]{E}  {m}")
def info(m):     print(f"  {Y}[..]{E}     {m}")
def section(t):  print(f"\n{BOLD}{'='*58}\n  {t}\n{'='*58}{E}")

def run(cmd, stop=True):
    info(f"$ {cmd}")
    r = subprocess.run(
        cmd, shell=True, cwd=ROOT,
        capture_output=True, text=True,
        env={**os.environ, 'DJANGO_SETTINGS_MODULE': 'academic_system.settings'}
    )
    for line in r.stdout.strip().split('\n'):
        if line.strip(): print(f"    {line}")
    if r.returncode != 0:
        err(f"FAILED: {cmd}")
        for line in r.stderr.strip().split('\n'):
            if line.strip(): print(f"    {R}{line}{E}")
        if stop: sys.exit(1)
    return r.returncode == 0

def write(path, content):
    full = os.path.join(ROOT, path.replace('/', os.sep))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')
    ok(f"Wrote: {path}")

def touch(path):
    full = os.path.join(ROOT, path.replace('/', os.sep))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    if not os.path.exists(full):
        open(full, 'w').close()
        ok(f"Created: {path}")

def delete(path):
    full = os.path.join(ROOT, path.replace('/', os.sep))
    if os.path.exists(full):
        os.remove(full)
        ok(f"Deleted: {path}")

def delete_dir(path):
    full = os.path.join(ROOT, path.replace('/', os.sep))
    if os.path.exists(full):
        shutil.rmtree(full)
        ok(f"Deleted dir: {path}")

def clean_migrations(app):
    d = os.path.join(ROOT, 'apps', app, 'migrations')
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f != '__init__.py' and f.endswith('.py'):
                os.remove(os.path.join(d, f))
                ok(f"Deleted migration: apps/{app}/migrations/{f}")

def clear_pycache():
    for dp, dns, _ in os.walk(ROOT):
        for dn in list(dns):
            if dn == '__pycache__':
                shutil.rmtree(os.path.join(dp, dn), ignore_errors=True)
    ok("Cleared __pycache__")


print(f"\n{BOLD}{'='*58}")
print("  Academic Management System — Fix & Run  v7")
print(f"{'='*58}{E}")


# ── 1. settings.py ───────────────────────────────────────────────
section("1  Writing settings.py")
write('academic_system/settings.py', """
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = config('SECRET_KEY',
    default='django-insecure-ams-2026-xyz987654321-replace-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_extensions',
    'apps.accounts.apps.AccountsConfig',
    'apps.core.apps.CoreConfig',
    'apps.courses.apps.CoursesConfig',
    'apps.grades.apps.GradesConfig',
    'apps.attendance.apps.AttendanceConfig',
    'apps.assignments.apps.AssignmentsConfig',
]

AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'academic_system.urls'
WSGI_APPLICATION = 'academic_system.wsgi.application'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

DATABASES = {'default': {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': BASE_DIR / 'db.sqlite3',
}}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary', messages.INFO: 'info',
    messages.SUCCESS: 'success', messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}
""")


# ── 2. apps.py files ─────────────────────────────────────────────
section("2  Writing apps.py files")
for app, label, name in [
    ('accounts',    'accounts',    'Accounts'),
    ('core',        'core',        'Core'),
    ('courses',     'courses',     'Courses'),
    ('grades',      'grades',      'Grades'),
    ('attendance',  'attendance',  'Attendance'),
    ('assignments', 'assignments', 'Assignments'),
]:
    write(f'apps/{app}/apps.py', f"""
from django.apps import AppConfig

class {name.replace(' ','')}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.{app}'
    label = '{label}'
    verbose_name = '{name}'
""")


# ── 3. __init__.py files ─────────────────────────────────────────
section("3  Creating __init__.py files")
for p in [
    'apps/__init__.py',
    'apps/accounts/__init__.py',
    # accounts/migrations intentionally omitted — accounts is unmigrated
    'apps/core/__init__.py',           'apps/core/migrations/__init__.py',
    'apps/courses/__init__.py',        'apps/courses/migrations/__init__.py',
    'apps/grades/__init__.py',         'apps/grades/migrations/__init__.py',
    'apps/attendance/__init__.py',     'apps/attendance/migrations/__init__.py',
    'apps/assignments/__init__.py',    'apps/assignments/migrations/__init__.py',
    'scripts/__init__.py',
]:
    touch(p)


# ── 4. Directories ───────────────────────────────────────────────
section("4  Creating directories")
for d in ['static/css', 'static/js', 'static/img', 'staticfiles', 'media']:
    os.makedirs(os.path.join(ROOT, d.replace('/', os.sep)), exist_ok=True)
    ok(f"Directory: {d}/")


# ── 5. Clean old state ───────────────────────────────────────────
section("5  Cleaning old database, migrations, pycache")
delete('db.sqlite3')
delete_dir('apps/accounts/migrations')
ok("accounts/migrations removed — accounts is now unmigrated (syncdb will create tables)")
for app in ['core', 'courses', 'grades', 'attendance', 'assignments']:
    clean_migrations(app)
clear_pycache()


# ── 6. makemigrations for other apps ─────────────────────────────
section("6  Running makemigrations (courses, grades, attendance, assignments)")
os.environ['DJANGO_SETTINGS_MODULE'] = 'academic_system.settings'
for app in ['courses', 'grades', 'attendance', 'assignments']:
    run(f'python manage.py makemigrations {app}')
run('python manage.py makemigrations core', stop=False)
clear_pycache()


# ── 7. Migrate + syncdb ──────────────────────────────────────────
section("7  Applying migrations + syncdb for accounts")
run('python manage.py migrate --run-syncdb')


# ── 8. Verify tables using ACTUAL model table names ───────────────
section("8  Verifying tables (using actual model db_table names)")
os.environ['DJANGO_SETTINGS_MODULE'] = 'academic_system.settings'

import django
django.setup()

from django.db import connection
connection.close()
existing_tables = set(connection.introspection.table_names())

info("All tables in database:")
for t in sorted(existing_tables):
    print(f"    {t}")

# Import models and get their ACTUAL table names
from apps.accounts.models import User, Department, StudentProfile, ProfessorProfile
from apps.courses.models import Course, Enrollment, Announcement
from apps.grades.models import Grade, GradeComponent
from apps.attendance.models import AttendanceSession, AttendanceRecord, AttendanceSummary
from apps.assignments.models import Assignment, AssignmentSubmission, SubmissionComment

models_to_check = [
    (User,               'User'),
    (Department,         'Department'),
    (StudentProfile,     'StudentProfile'),
    (ProfessorProfile,   'ProfessorProfile'),
    (Course,             'Course'),
    (Enrollment,         'Enrollment'),
    (Announcement,       'Announcement'),
    (Grade,              'Grade'),
    (GradeComponent,     'GradeComponent'),
    (AttendanceSession,  'AttendanceSession'),
    (AttendanceRecord,   'AttendanceRecord'),
    (AttendanceSummary,  'AttendanceSummary'),
    (Assignment,         'Assignment'),
    (AssignmentSubmission, 'AssignmentSubmission'),
    (SubmissionComment,  'SubmissionComment'),
]

print()
missing = []
for model_cls, name in models_to_check:
    table = model_cls._meta.db_table
    if table in existing_tables:
        ok(f"{table}  ({name})")
    else:
        err(f"MISSING: {table}  ({name})")
        missing.append((table, name))

if missing:
    print()
    err(f"{len(missing)} tables still missing:")
    for t, n in missing:
        print(f"    - {t}  ({n})")
    print()
    info("This means syncdb did not create these tables.")
    info("Accounts models might have an error. Checking...")
    run('python manage.py check', stop=False)
    sys.exit(1)

ok(f"\n  All {len(models_to_check)} model tables verified!")


# ── 9. Write clean seed_data.py (no patching, always correct) ────
section("9  Writing clean seed_data.py")

# Get actual table names from models
actual_tables = {m.__name__: m._meta.db_table for m, _ in models_to_check}
ok("Detected table names from models:")
for model_name, table in actual_tables.items():
    info(f"  {model_name} → {table}")

# Write seed_data.py with the CORRECT table names baked in
user_table        = actual_tables['User']
dept_table        = actual_tables['Department']
student_table     = actual_tables['StudentProfile']
professor_table   = actual_tables['ProfessorProfile']
course_table      = actual_tables['Course']
enroll_table      = actual_tables['Enrollment']
announce_table    = actual_tables['Announcement']
grade_table       = actual_tables['Grade']
grade_comp_table  = actual_tables['GradeComponent']
att_sess_table    = actual_tables['AttendanceSession']
att_rec_table     = actual_tables['AttendanceRecord']
att_sum_table     = actual_tables['AttendanceSummary']
assign_table      = actual_tables['Assignment']
submission_table  = actual_tables['AssignmentSubmission']
comment_table     = actual_tables['SubmissionComment']

write('scripts/seed_data.py', f"""
\"\"\"
scripts/seed_data.py  —  Seed data for Academic Management System.
Auto-generated by fix_and_run.py with correct table names.

Usage:
    python scripts/seed_data.py
\"\"\"

import os, sys, random
from datetime import date, timedelta, time
from decimal import Decimal

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_system.settings')

import django
django.setup()

from django.utils import timezone
from django.db import transaction, connection

from apps.accounts.models import User, UserRole, Department, StudentProfile, ProfessorProfile
from apps.courses.models import Course, Enrollment, Announcement
from apps.grades.models import Grade, GradeComponent, GradeHistory
from apps.attendance.models import AttendanceSession, AttendanceRecord, AttendanceSummary
from apps.assignments.models import Assignment, AssignmentSubmission, SubmissionComment


def ok(m):      print(f"  [OK]  {{m}}")
def section(t): print(f"\\n{{'='*50}}\\n  {{t}}\\n{{'='*50}}")


def check_tables():
    required = [
        '{user_table}', '{dept_table}',
        '{student_table}', '{professor_table}',
        '{course_table}', '{enroll_table}', '{announce_table}',
        '{grade_table}', '{grade_comp_table}',
        '{att_sess_table}', '{att_rec_table}', '{att_sum_table}',
        '{assign_table}', '{submission_table}', '{comment_table}',
    ]
    existing = connection.introspection.table_names()
    missing = [t for t in required if t not in existing]
    if missing:
        print("\\n[ERROR] Missing tables:")
        for t in missing:
            print(f"  - {{t}}")
        print("\\nRun: python fix_and_run.py")
        sys.exit(1)
    ok(f"All {{len(required)}} required tables found.")


@transaction.atomic
def seed():
    print("\\n" + "="*50)
    print("  Academic Management System - Seed Data")
    print("="*50)

    section("Checking tables")
    check_tables()

    section("Clearing existing data")
    for model in [SubmissionComment, AssignmentSubmission, Assignment,
                  AttendanceSummary, AttendanceRecord, AttendanceSession,
                  GradeHistory, GradeComponent, Grade,
                  Announcement, Enrollment, Course,
                  StudentProfile, ProfessorProfile, Department]:
        count = model.objects.count()
        model.objects.all().delete()
        ok(f"Cleared {{count}} {{model.__name__}}")
    deleted, _ = User.objects.filter(is_superuser=False).delete()
    ok(f"Cleared {{deleted}} User records")

    section("Creating Departments")
    dept_data = [
        ("Computer Science",   "CS",   "Computation, algorithms, software."),
        ("Mathematics",        "MATH", "Pure and applied mathematics."),
        ("Physics",            "PHY",  "Fundamental laws of nature."),
        ("English Literature", "ENG",  "Language, writing, literature."),
        ("Business Admin",     "BUS",  "Management, finance, organisations."),
        ("Engineering",        "ENG2", "Applied engineering disciplines."),
    ]
    departments = {{}}
    for name, code, desc in dept_data:
        d = Department.objects.create(name=name, code=code, description=desc)
        departments[code] = d
        ok(f"Department: {{code}} - {{name}}")

    section("Creating Admin")
    admin = User.objects.create_superuser(
        email="admin@ams.edu", password="Admin@1234",
        first_name="System", last_name="Administrator", role=UserRole.ADMIN,
    )
    ok(f"Admin: {{admin.email}} / Admin@1234")

    section("Creating Professors")
    prof_data = [
        ("alice.johnson", "Alice","Johnson","CS",  "full",      "AI & ML"),
        ("bob.smith",     "Bob",  "Smith",  "MATH","associate", "Calculus"),
        ("carol.white",   "Carol","White",  "PHY", "assistant", "Quantum Mechanics"),
        ("david.brown",   "David","Brown",  "ENG", "lecturer",  "Creative Writing"),
        ("eve.davis",     "Eve",  "Davis",  "BUS", "associate", "Financial Management"),
        ("frank.miller",  "Frank","Miller", "CS",  "assistant", "Web Dev"),
        ("grace.wilson",  "Grace","Wilson", "ENG2","full",      "Structural Engineering"),
    ]
    professors = []
    for i, (uname, first, last, dept, rank, spec) in enumerate(prof_data, 1):
        u = User.objects.create_user(
            email=f"{{uname}}@ams.edu", password="Prof@1234",
            first_name=first, last_name=last, role=UserRole.PROFESSOR,
            phone=f"+1555{{i:07d}}", bio=f"Specializes in {{spec}}.",
        )
        p = ProfessorProfile.objects.create(
            user=u, employee_id=f"EMP-{{2020+i}}-{{i:03d}}",
            department=departments[dept], rank=rank, specialization=spec,
            office_location=f"Building {{chr(64+i)}}, Room {{100+i*10}}",
            office_hours="Mon/Wed 2-4 PM", hire_date=date(2018+i%5, i%12+1, 1),
        )
        professors.append((u, p))
        ok(f"Professor: {{u.email}} / Prof@1234")
    departments["CS"].head = professors[0][0]; departments["CS"].save()
    departments["MATH"].head = professors[1][0]; departments["MATH"].save()

    section("Creating 40 Students")
    firsts = ["James","Mary","John","Patricia","Robert","Jennifer","Michael","Linda",
              "William","Barbara","David","Susan","Richard","Jessica","Joseph","Sarah",
              "Thomas","Karen","Charles","Lisa","Christopher","Nancy","Daniel","Betty",
              "Matthew","Margaret","Anthony","Sandra","Mark","Ashley","Donald","Emily",
              "Steven","Kimberly","Paul","Donna","Andrew","Carol","Joshua","Ruth"]
    lasts  = ["Anderson","Thomas","Jackson","White","Harris","Martin","Garcia","Thompson",
              "Martinez","Robinson","Clark","Rodriguez","Lewis","Lee","Walker","Hall",
              "Allen","Young","Hernandez","King","Wright","Lopez","Hill","Scott",
              "Green","Adams","Baker","Gonzalez","Nelson","Carter","Mitchell","Perez",
              "Roberts","Turner","Phillips","Campbell","Parker","Evans","Edwards","Collins"]
    students = []
    used = set()
    for i in range(1, 41):
        while True:
            f, l = random.choice(firsts), random.choice(lasts)
            if (f, l) not in used: used.add((f, l)); break
        yr = random.randint(1, 4)
        dc = random.choice(["CS","MATH","PHY","ENG","BUS","ENG2"])
        u = User.objects.create_user(
            email=f"{{f.lower()}}.{{l.lower()}}{{i:02d}}@student.ams.edu",
            password="Student@1234", first_name=f, last_name=l,
            role=UserRole.STUDENT, phone=f"+1444{{i:07d}}",
            date_of_birth=date(2000+random.randint(0,5), random.randint(1,12), random.randint(1,28)),
        )
        p = StudentProfile.objects.create(
            user=u, student_id=f"STU-2024-{{i:04d}}",
            department=departments[dc], year_of_study=yr,
            enrollment_date=date(2024-yr+1, 8, 15),
            expected_graduation=date(2024-yr+5, 5, 15),
            status='active', scholarship=random.random()<0.15,
            emergency_contact_name=f"Parent of {{f}}",
            emergency_contact_phone=f"+1333{{i:07d}}",
        )
        students.append((u, p))
    ok(f"Created {{len(students)}} students  [password: Student@1234]")

    section("Creating Courses")
    cdata = [
        ("CS101","Introduction to CS",        0,"CS",  3,35,"Mon,Wed,Fri",time(9,0), time(9,50), "CS-101","in_person"),
        ("CS201","Data Structures",            0,"CS",  3,30,"Tue,Thu",    time(10,0),time(11,30),"CS-201","in_person"),
        ("CS301","Database Systems",           5,"CS",  3,28,"Mon,Wed",    time(14,0),time(15,30),"CS-102","in_person"),
        ("CS401","Machine Learning",           0,"CS",  3,25,"Mon,Wed,Fri",time(13,0),time(13,50),"CS-301","hybrid"),
        ("MATH101","Calculus I",               1,"MATH",4,40,"Mon,Wed,Fri",time(8,0), time(8,50), "M-101","in_person"),
        ("MATH201","Linear Algebra",           1,"MATH",3,30,"Tue,Thu",    time(13,0),time(14,30),"M-201","in_person"),
        ("MATH301","Probability & Statistics", 1,"MATH",3,35,"Mon,Wed",    time(10,0),time(11,30),"M-301","in_person"),
        ("PHY101","Physics I",                 2,"PHY", 4,38,"Mon,Wed,Fri",time(11,0),time(11,50),"P-101","in_person"),
        ("ENG101","English Composition",       3,"ENG", 3,30,"Tue,Thu",    time(9,0), time(10,30),"E-101","in_person"),
        ("ENG201","World Literature",          3,"ENG", 3,25,"Mon,Wed,Fri",time(15,0),time(15,50),"E-201","in_person"),
        ("BUS101","Principles of Business",    4,"BUS", 3,45,"Tue,Thu",    time(11,0),time(12,30),"B-101","in_person"),
        ("BUS301","Financial Accounting",      4,"BUS", 3,30,"Mon,Wed,Fri",time(10,0),time(10,50),"B-201","hybrid"),
        ("CS501","Advanced Web Dev",           5,"CS",  3,20,"Tue,Thu",    time(14,0),time(15,30),"CS-Lab","in_person"),
        ("ENG301","Creative Writing",          3,"ENG", 3,20,"Mon,Wed",    time(13,0),time(14,30),"E-301","in_person"),
        ("PHY201","Physics II",                2,"PHY", 4,32,"Mon,Wed,Fri",time(9,0), time(9,50), "P-201","in_person"),
    ]
    courses = []
    for code,title,pi,dc,cr,mx,days,st,et,room,mode in cdata:
        c = Course.objects.create(
            course_code=code, title=title,
            description=f"Covers {{title.lower()}} through lectures and projects.",
            professor=professors[pi][0], department=departments[dc],
            academic_year="2025-2026", semester="Spring",
            credits=cr, max_students=mx, schedule_days=days,
            start_time=st, end_time=et, room=room, delivery_mode=mode,
            status="active", is_active=True,
            start_date=date(2026,1,13), end_date=date(2026,5,10),
        )
        courses.append(c)
        ok(f"Course: {{code}} - {{title}}")

    section("Creating Grade Components")
    for course in courses:
        for nm,ct,w,ms,o in [("Midterm","midterm",30,100,1),("Final","final",40,100,2),
                               ("Assignments","assignment",20,100,3),("Participation","participation",10,100,4)]:
            GradeComponent.objects.create(course=course,name=nm,component_type=ct,weight=w,max_score=ms,order=o)
    ok(f"Created {{len(courses)*4}} grade components")

    section("Creating Enrollments")
    ec = 0
    se = {{sp.pk: [] for _, sp in students}}
    for _, sp in students:
        for course in random.sample(courses, min(random.randint(3,5), len(courses))):
            if course.enrolled_count >= course.max_students: continue
            e = Enrollment.objects.create(
                student=sp, course=course, status='enrolled',
                enrollment_date=timezone.now()-timedelta(days=random.randint(30,90)),
            )
            AttendanceSummary.objects.get_or_create(enrollment=e)
            se[sp.pk].append(e); ec += 1
    ok(f"Created {{ec}} enrollments")

    section("Creating Announcements")
    ac = 0
    atpl = [
        ("Midterm Exam Schedule","exam","high","Midterm is next week. Review chapters 1-6."),
        ("Assignment Due Date","assignment","normal","Assignment 2 due this Friday 11:59 PM."),
        ("Office Hours Update","general","normal","Office hours moved to Wednesday 3-5 PM."),
        ("Grade Release","grade","normal","Midterm grades released. Check your report."),
        ("Final Exam Info","exam","urgent","Final exam covers all semester material."),
    ]
    for course in courses:
        for i,(t,at,p,c) in enumerate(random.sample(atpl, min(random.randint(2,4),len(atpl)))):
            Announcement.objects.create(
                course=course, author=course.professor,
                title=f"{{t}} - {{course.course_code}}",
                content=f"{{c}}\\n\\nBest regards,\\n{{course.professor.get_full_name()}}",
                announcement_type=at, priority=p, is_pinned=(i==0),
                publish_at=timezone.now()-timedelta(days=random.randint(1,45)),
            ); ac += 1
    ok(f"Created {{ac}} announcements")

    section("Creating Assignments")
    atpls = [
        ("Homework 1","homework",100,20,-20,"published"),
        ("Homework 2","homework",100,15,-10,"published"),
        ("Midterm Project","project",150,10,5,"published"),
        ("Quiz 1","quiz",50,25,-5,"published"),
        ("Quiz 2","quiz",50,12,3,"published"),
        ("Final Project","project",200,5,30,"published"),
        ("Lab Report","lab",100,30,-3,"published"),
        ("Essay","essay",100,20,7,"published"),
    ]
    all_assignments = []
    for course in courses:
        for t,at,ms,da,dd,st in random.sample(atpls, min(random.randint(4,6),len(atpls))):
            a = Assignment.objects.create(
                course=course, created_by=course.professor,
                title=f"{{t}} - {{course.course_code}}",
                description=f"Complete {{t.lower()}} per syllabus guidelines.",
                assignment_type=at, status=st,
                max_score=Decimal(str(ms)),
                weight=Decimal(str(random.choice([5,10,15,20]))),
                assigned_date=timezone.now()-timedelta(days=da),
                due_date=timezone.now()+timedelta(days=dd),
                late_submission_allowed=random.random()<0.4,
                late_penalty_percent=Decimal("10.00"),
                submission_format="PDF, DOCX",
            )
            all_assignments.append(a)
    ok(f"Created {{len(all_assignments)}} assignments")

    section("Creating Submissions")
    sc2=0; gc2=0
    for _,sp in students:
        for e in se[sp.pk]:
            for a in [x for x in all_assignments if x.course_id==e.course_id and x.status=='published']:
                if random.random()<0.25: continue
                is_late = a.due_date<timezone.now() and random.random()<0.1
                sat = min(
                    a.due_date+timedelta(hours=random.randint(1,24)) if is_late
                    else a.due_date-timedelta(days=random.randint(1,5)),
                    timezone.now()
                )
                score=None; isg=False
                if a.due_date<timezone.now() and random.random()<0.85:
                    score=Decimal(str(round(random.uniform(55,100),2))); isg=True; gc2+=1
                AssignmentSubmission.objects.create(
                    assignment=a, student=sp,
                    submission_text=f"Submission for {{a.title}}.",
                    status='graded' if isg else ('late' if is_late else 'submitted'),
                    submitted_at=sat, is_late=is_late,
                    score=score, adjusted_score=score, is_graded=isg,
                    graded_by=a.course.professor if isg else None,
                    graded_at=timezone.now()-timedelta(days=random.randint(0,5)) if isg else None,
                    feedback=f"Score: {{score}}/{{a.max_score}}." if isg else "",
                ); sc2+=1
    ok(f"Created {{sc2}} submissions ({{gc2}} graded)")

    section("Creating Attendance")
    sess_c=0; rec_c=0
    topics=["Introduction","Core Concepts","Lab Session","Workshop","Review","Case Study","Exam Prep"]
    for course in courses:
        sdates=sorted({{date.today()-timedelta(days=random.randint(5,90)) for _ in range(random.randint(8,12))}})
        for i,sd in enumerate(sdates):
            sess=AttendanceSession.objects.create(
                course=course, date=sd, session_type='lecture',
                topic=topics[i%len(topics)], created_by=course.professor,
                is_locked=(i<len(sdates)-2),
            ); sess_c+=1
            for e in Enrollment.objects.filter(course=course,status='enrolled'):
                r=random.random()
                AttendanceRecord.objects.create(
                    session=sess, enrollment=e,
                    status='present' if r<0.78 else 'absent' if r<0.88 else 'late' if r<0.93 else 'excused' if r<0.97 else 'remote',
                    marked_by=course.professor,
                ); rec_c+=1
    ok(f"Created {{sess_c}} sessions, {{rec_c}} records")
    for s in AttendanceSummary.objects.all(): s.refresh()
    ok("Refreshed attendance summaries")

    section("Creating Grades")
    grc=0; fc=0
    for _,sp in students:
        for e in se[sp.pk]:
            if random.random()<0.2: continue
            num=max(Decimal("45"),min(Decimal("100"),Decimal(str(round(random.gauss(76,12),2)))))
            let=Grade.score_to_letter(num)
            gp=Decimal(str(Grade.GPA_POINTS.get(let,0.00)))
            isf=random.random()<0.65
            Grade.objects.create(
                enrollment=e, graded_by=e.course.professor,
                numeric_score=num, letter_grade=let, grade_points=gp,
                midterm_score=max(Decimal("0"),min(Decimal("100"),Decimal(str(round(float(num)*random.uniform(0.85,1.15),2))))),
                final_score=max(Decimal("0"),min(Decimal("100"),Decimal(str(round(float(num)*random.uniform(0.85,1.15),2))))),
                assignment_score=Decimal(str(round(random.uniform(60,100),2))),
                quiz_score=Decimal(str(round(random.uniform(60,100),2))),
                participation_score=Decimal(str(round(random.uniform(70,100),2))),
                is_finalized=isf,
                remarks=random.choice(["Excellent work.","Good understanding.","Room for improvement.","Strong analytical skills."]),
                graded_at=timezone.now()-timedelta(days=random.randint(1,30)),
                finalized_at=timezone.now()-timedelta(days=random.randint(0,10)) if isf else None,
            ); grc+=1
            if isf: fc+=1
    ok(f"Created {{grc}} grades ({{fc}} finalized)")

    section("Updating GPAs")
    for _,sp in students: sp.update_gpa()
    ok(f"Updated {{len(students)}} student GPAs")

    print("\\n"+"="*50)
    print("  SEED COMPLETE")
    print("="*50)
    print(f"  Departments: {{Department.objects.count()}}")
    print(f"  Users:       1 admin + {{len(professors)}} professors + {{len(students)}} students")
    print(f"  Courses:     {{Course.objects.count()}}")
    print(f"  Enrollments: {{Enrollment.objects.count()}}")
    print(f"  Grades:      {{Grade.objects.count()}}")
    print(f"  Assignments: {{Assignment.objects.count()}}")
    print()
    print("  Login Credentials:")
    print("  Admin:     admin@ams.edu          / Admin@1234")
    print("  Professor: alice.johnson@ams.edu  / Prof@1234")
    print(f"  Student:   {{students[0][0].email}} / Student@1234")
    print("="*50)


if __name__ == '__main__':
    seed()
else:
    seed()
""")


# ── 10. Run seed ─────────────────────────────────────────────────
section("10 Running seed data")
run('python scripts/seed_data.py')


# ── Done ─────────────────────────────────────────────────────────
print(f"\n{BOLD}{'='*58}")
print(f"  {G}SETUP COMPLETE!{E}")
print(f"{'='*58}{E}")
print(f"\n  {BOLD}python manage.py runserver{E}")
print(f"  http://127.0.0.1:8000\n")
print(f"  {G}Admin    :{E}  admin@ams.edu          /  Admin@1234")
print(f"  {G}Professor:{E}  alice.johnson@ams.edu  /  Prof@1234")
print(f"  {G}Student  :{E}  (shown in seed output) /  Student@1234")
print(f"{BOLD}{'='*58}{E}\n")