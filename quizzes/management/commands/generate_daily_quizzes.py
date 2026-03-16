"""
Management command: generate_daily_quizzes
==========================================
Automatically generates personalized daily quizzes for every active student
enrolled in every active course.

Usage:
    python manage.py generate_daily_quizzes
    python manage.py generate_daily_quizzes --dry-run          (preview only)
    python manage.py generate_daily_quizzes --course-id 3      (one course only)
    python manage.py generate_daily_quizzes --force            (regenerate even if quiz exists today)

Schedule this command via Windows Task Scheduler (see setup_daily_quiz_scheduler.bat).
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Auto-generates personalized daily quizzes for all active students "
        "enrolled in active courses. Safe to run multiple times -- skips "
        "students who already have an active quiz today."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without actually creating any quizzes.",
        )
        parser.add_argument(
            "--course-id",
            type=int,
            default=None,
            help="Limit generation to a single course by its ID.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Force-generate a new quiz even if the student already has an "
                "active (unexpired, incomplete) quiz today."
            ),
        )

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        from courses.models import Course
        from enrollments.models import Enrollment
        from quizzes.models import DailyQuiz
        from quizzes.services import DailyQuizService
        from django.contrib.auth import get_user_model

        User = get_user_model()
        dry_run = options["dry_run"]
        force   = options["force"]
        course_id_filter = options["course_id"]

        now = timezone.now()
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n[%s] Daily Quiz Auto-Generation Started" % now.strftime("%Y-%m-%d %H:%M")
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("  [DRY-RUN] No quizzes will be created.\n"))

        # 1. Resolve target courses
        if course_id_filter:
            courses = Course.objects.filter(id=course_id_filter, status="active")
            if not courses.exists():
                raise CommandError(
                    "No active course found with id=%d." % course_id_filter
                )
        else:
            courses = Course.objects.filter(status="active")

        total_courses = courses.count()
        self.stdout.write("  Courses to process : %d" % total_courses)

        # 2. Walk every course -> every active student
        created_count  = 0
        skipped_count  = 0
        error_count    = 0
        notified_count = 0

        for course in courses:
            student_ids = (
                Enrollment.objects
                .filter(batch__course=course, status="active")
                .values_list("student_id", flat=True)
                .distinct()
            )

            if not student_ids.exists():
                continue

            self.stdout.write("\n  Course: %s -- %s" % (course.code, course.title))
            self.stdout.write("    Students: %d" % student_ids.count())

            for student_id in student_ids:
                try:
                    student = User.objects.get(pk=student_id)
                except User.DoesNotExist:
                    continue

                # Skip if quiz already exists (unless --force)
                if not force:
                    existing = DailyQuiz.objects.filter(
                        student=student,
                        course=course,
                        expires_at__gt=now,
                        is_completed=False,
                    ).first()
                    if existing:
                        skipped_count += 1
                        self.stdout.write(
                            "    [SKIP] %s -- active quiz already exists." % student.username
                        )
                        continue

                # Dry-run: just count, don't create
                if dry_run:
                    self.stdout.write(
                        "    [DRY-RUN] Would generate quiz for %s." % student.username
                    )
                    created_count += 1
                    continue

                # Generate the quiz
                try:
                    svc = DailyQuizService(student, course)
                    daily_quiz = svc.get_or_create_daily_quiz()
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            "    [OK] %s -> \"%s\" (%d questions)"
                            % (
                                student.username,
                                daily_quiz.topic_name,
                                daily_quiz.quiz.questions.count(),
                            )
                        )
                    )

                    # Send in-app notification
                    try:
                        from notifications.services import notify_user
                        from django.urls import reverse
                        notify_user(
                            user=student,
                            title="Your Daily Quiz is Ready!",
                            message=(
                                "Your personalised daily quiz for %s is ready. "
                                "Topic: %s. Keep your streak alive!"
                                % (course.code, daily_quiz.topic_name)
                            ),
                            n_type="QUIZ_REMINDER",
                            link=reverse(
                                "quizzes:take",
                                kwargs={"quiz_id": daily_quiz.quiz.id},
                            ),
                        )
                        notified_count += 1
                    except Exception as notify_err:
                        logger.warning(
                            "Notification failed for %s: %s" % (student.username, notify_err)
                        )

                except Exception as e:
                    error_count += 1
                    logger.error(
                        "Failed to generate daily quiz for student=%s, course=%s: %s"
                        % (student.username, course.code, e),
                        exc_info=True,
                    )
                    self.stdout.write(
                        self.style.ERROR(
                            "    [ERROR] %s -- %s" % (student.username, e)
                        )
                    )

        # 3. Final summary
        self.stdout.write("\n" + "-" * 55)
        mode = "DRY-RUN " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                "  %sSummary:\n"
                "    [CREATED]  : %d\n"
                "    [SKIPPED]  : %d\n"
                "    [NOTIFIED] : %d\n"
                "    [ERRORS]   : %d"
                % (mode, created_count, skipped_count, notified_count, error_count)
            )
        )
        self.stdout.write("-" * 55 + "\n")
