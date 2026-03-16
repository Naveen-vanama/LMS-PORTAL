from django.core.management.base import BaseCommand
from quizzes.revision_service import RevisionQuizService

class Command(BaseCommand):
    help = 'Checks courses for instructor inactivity and generates revision quizzes if needed.'

    def handle(self, *args, **options):
        self.stdout.write("Checking for inactive courses...")
        service = RevisionQuizService()
        count = service.trigger_batch_revision_quizzes()
        self.stdout.write(self.style.SUCCESS(f"Successfully generated revision quizzes for {count} courses."))
