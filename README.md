# Academic Management System

A full-featured, role-based Academic Management System built with **Django 4.2**.

## Roles
| Role | Capabilities |
|------|-------------|
| **Admin** | Full system access, user/department management, grade overrides |
| **Professor** | Course management, grading, attendance, assignments |
| **Student** | Enroll in courses, submit assignments, view grades & attendance |

## Tech Stack
- **Backend:** Django 4.2 (LTS), Python 3.10+
- **Frontend:** Bootstrap 5, Font Awesome 6, custom CSS/JS
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Auth:** Custom AbstractBaseUser with email login + role system

## Quick Start
```bash
cd AcademicSystem

venv\Scripts\activate

python fix_and_run.py

python manage.py runserver

```
Open **http://127.0.0.1:8000** — 
login with `admin@ams.edu` / `Admin@1234`                  |
login with `david.brown@ams.edu` / `Prof@1234` (For more professor e-mails you can check in admin panel) |
for students check admin panel and default password for students is `Student@1234` |
