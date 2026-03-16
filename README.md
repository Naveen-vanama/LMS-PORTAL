# CollegePortal – Django Project (Python 3.14 Compatible)

A full-featured college management web portal built with Django.

## Features

| Module | Capabilities |
|---|---|
| **Users** | Custom user model with Admin / Instructor / Student roles, login, registration, profile |
| **Courses** | Course CRUD, Batch management, Student Groups |
| **Enrollments** | Self-enrollment, waitlisting, grade entry |
| **Resources** | File uploads & external links per course/batch |
| **Attendance** | Session-based attendance, per-student reports |

## Setup

```bash
# 1. Create & activate virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply migrations
python manage.py migrate

# 4. Create a superuser (Admin role)
python manage.py createsuperuser

# 5. Run dev server
python manage.py runserver
```

Then open http://127.0.0.1:8000 in your browser.

## Project Structure

```
collegeportal/
├── myproject/          # Django project config (settings, urls, wsgi)
├── users/              # CustomUser model + auth views (login/register/dashboard)
├── courses/            # Course, Batch, Group models & views
├── enrollments/        # Enrollment model (student ↔ batch), grade entry
├── resources/          # FileResource model, upload/download
├── attendance/         # AttendanceSession + AttendanceRecord, reporting
├── templates/          # All HTML templates (Bootstrap 5 + sidebar layout)
├── static/             # CSS / JS / images
└── media/              # Uploaded files (gitignored in production)
```

## Role Permissions

| Action | Admin | Instructor | Student |
|---|:---:|:---:|:---:|
| Create/edit courses | ✅ | — | — |
| Create batches | ✅ | Own courses | — |
| Upload resources | ✅ | Own courses | — |
| Take attendance | ✅ | Own courses | — |
| Enroll in batches | — | — | ✅ |
| View resources | ✅ | ✅ | Enrolled only |
| View attendance report | ✅ | ✅ | Own only |

## Configuration Notes

- Change `SECRET_KEY` in `settings.py` for production (use an environment variable).
- Switch `DATABASES` from SQLite to PostgreSQL for production.
- Set `DEBUG=False` and configure `ALLOWED_HOSTS` properly for deployment.
- Use `python manage.py collectstatic` before deploying.
