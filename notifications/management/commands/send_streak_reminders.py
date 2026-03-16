from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import CustomUser
from quizzes.models import StudentStreak
from notifications.services import notify_user
from django.urls import reverse
from django.conf import settings

class Command(BaseCommand):
    help = 'Sends notifications to students who haven\'t completed a quiz today'

    def handle(self, *args, **options):
        today = timezone.now().date()
        students = CustomUser.objects.filter(role='student')
        count = 0

        for student in students:
            streak = StudentStreak.objects.filter(student=student).first()
            
            # If no streak entry or last quiz was not today
            if not streak or streak.last_quiz_date != today:
                notify_user(
                    user=student,
                    title="Don't break your streak! 🔥",
                    message="You haven't completed a quiz today. Take a quick quiz now to keep your streak alive!",
                    n_type='STREAK_REMINDER',
                    link=reverse('courses:list')
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully sent {count} streak reminders.'))
