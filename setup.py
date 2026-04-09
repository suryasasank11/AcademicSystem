"""
setup.py - Run this ONCE to set up the entire project automatically.

Usage:
    python setup.py

This script will:
1. Verify Django is installed
2. Delete old database and migrations
3. Create all migrations in correct order
4. Apply all migrations
5. Verify accounts table exists
6. Run seed data
7. Tell you how to start the server
"""

import os
import sys
import shutil
import subprocess

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

def run(cmd, stop_on_error=True):
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT)
    if result.returncode != 0 and stop_on_error:
        print(f"\n[ERROR] Command failed: {cmd}")
        print("Fix the error above and run setup.py again.")
        sys.exit(1)
    return result.returncode

def delete_file(path):
    full = os.path.join(PROJECT_ROOT, path)
    if os.path.exists(full):
        os.remove(full)
        print(f"  Deleted: {path}")

def delete_migrations_in(app_path):
    mig_dir = os.path.join(PROJECT_ROOT, app_path, 'migrations')
    if not os.path.exists(mig_dir):
        os.makedirs(mig_dir)
        open(os.path.join(mig_dir, '__init__.py'), 'w').close()
        return
    for f in os.listdir(mig_dir):
        if f != '__init__.py' and f.endswith('.py'):
            os.remove(os.path.join(mig_dir, f))
            print(f"  Deleted migration: {app_path}/migrations/{f}")
    # Ensure __init__.py exists
    init = os.path.join(mig_dir, '__init__.py')
    if not os.path.exists(init):
        open(init, 'w').close()

def ensure_init(path):
    full = os.path.join(PROJECT_ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    if not os.path.exists(full):
        open(full, 'w').close()
        print(f"  Created: {path}")

print("=" * 55)
print("  Academic Management System — Automated Setup")
print("=" * 55)

# Step 1 — Check Django installed
print("\n[1/7] Checking Django installation...")
try:
    import django
    print(f"  Django {django.__version__} found.")
except ImportError:
    print("  Django not found. Run: pip install -r requirements.txt")
    sys.exit(1)

# Step 2 — Ensure all __init__.py files exist
print("\n[2/7] Ensuring package files exist...")
for path in [
    'apps/__init__.py',
    'apps/accounts/__init__.py',
    'apps/accounts/migrations/__init__.py',
    'apps/core/__init__.py',
    'apps/core/migrations/__init__.py',
    'apps/courses/__init__.py',
    'apps/courses/migrations/__init__.py',
    'apps/grades/__init__.py',
    'apps/grades/migrations/__init__.py',
    'apps/attendance/__init__.py',
    'apps/attendance/migrations/__init__.py',
    'apps/assignments/__init__.py',
    'apps/assignments/migrations/__init__.py',
]:
    ensure_init(path)

# Step 3 — Create static/media directories
print("\n[3/7] Creating required directories...")
for d in ['static/css', 'static/js', 'static/img', 'staticfiles', 'media']:
    os.makedirs(os.path.join(PROJECT_ROOT, d), exist_ok=True)
    print(f"  Created: {d}/")

# Step 4 — Delete old database and migrations
print("\n[4/7] Cleaning old database and migrations...")
delete_file('db.sqlite3')
for app in ['accounts', 'core', 'courses', 'grades', 'attendance', 'assignments']:
    delete_migrations_in(f'apps/{app}')

# Step 5 — Verify settings has AUTH_USER_MODEL
print("\n[5/7] Verifying settings.py...")
settings_path = os.path.join(PROJECT_ROOT, 'academic_system', 'settings.py')
with open(settings_path, 'r') as f:
    settings_content = f.read()

if "AUTH_USER_MODEL = 'accounts.User'" not in settings_content:
    print("  WARNING: AUTH_USER_MODEL not found. Adding it now...")
    with open(settings_path, 'a') as f:
        f.write("\n\nAUTH_USER_MODEL = 'accounts.User'\n")
    print("  AUTH_USER_MODEL added to settings.py")
else:
    print("  AUTH_USER_MODEL = 'accounts.User'  [OK]")

# Step 6 — Run makemigrations in correct order
print("\n[6/7] Creating migrations...")
# accounts must be first — all other apps depend on User model
run("python manage.py makemigrations accounts")
run("python manage.py makemigrations courses")
run("python manage.py makemigrations grades")
run("python manage.py makemigrations attendance")
run("python manage.py makemigrations assignments")
run("python manage.py makemigrations core")

# Step 7 — Apply migrations
print("\n[7/7] Applying migrations...")
run("python manage.py migrate")

# Verify accounts table was created
print("\nVerifying accounts table...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_system.settings')
django.setup()

from django.db import connection
tables = connection.introspection.table_names()
if 'auth_user' in tables:
    print("  auth_user table exists  [OK]")
else:
    print("  [ERROR] auth_user table NOT found!")
    print("  This means AUTH_USER_MODEL is still not being picked up.")
    print("  Open academic_system/settings.py and confirm this line exists:")
    print("  AUTH_USER_MODEL = 'accounts.User'")
    sys.exit(1)

# Run seed data
print("\nRunning seed data...")
run("python scripts/seed_data.py")

print("\n" + "=" * 55)
print("  SETUP COMPLETE!")
print("=" * 55)
print("\n  Start the server with:")
print("  python manage.py runserver")
print("\n  Then open: http://127.0.0.1:8000")
print("\n  Login credentials:")
print("  Admin:     admin@ams.edu          / Admin@1234")
print("  Professor: alice.johnson@ams.edu  / Prof@1234")
print("  Student:   (shown in seed output) / Student@1234")
print("=" * 55)