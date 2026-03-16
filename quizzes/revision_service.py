import os
import json
import logging
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.db.models import Max
from django.contrib.auth import get_user_model
from courses.models import Course, Lesson
from resources.models import FileResource
from live_classes.models import LiveClass
from .models import Quiz, Question, StudentAnswer, RevisionQuiz
from notifications.services import notify_user
from django.urls import reverse

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

User = get_user_model()

class RevisionQuizService:
    def __init__(self, course_id=None):
        self.course_id = course_id
        self.api_key = getattr(settings, 'GOOGLE_API_KEY', os.environ.get('GOOGLE_API_KEY'))
        if self.api_key and genai:
            genai.configure(api_key=self.api_key)

    def check_instructor_inactivity(self, course):
        """Returns True if no new lesson, resource, or class for 14 days."""
        if not course.auto_revision_enabled:
            return False

        last_lesson = Lesson.objects.filter(course=course).aggregate(Max('created_at'))['created_at__max']
        last_resource = FileResource.objects.filter(course=course).aggregate(Max('created_at'))['created_at__max']
        last_class = LiveClass.objects.filter(course=course).aggregate(Max('created_at'))['created_at__max']

        check_dates = [d for d in [last_lesson, last_resource, last_class] if d]
        if not check_dates:
            # If nothing was ever uploaded, maybe don't trigger yet? 
            # Or if it's a new course, check course creation date.
            check_dates = [course.created_at]

        latest_activity = max(check_dates)
        days_inactive = (timezone.now() - latest_activity).days
        return days_inactive >= 14

    def get_weak_topics(self, student, course):
        """Identify topics where the student scored < 60%."""
        weak_lessons = []
        # Get quizzes taken by student in this course
        quizzes = Quiz.objects.filter(course=course, questions__student_answers__student=student).distinct()
        
        for quiz in quizzes:
            if not quiz.lesson:
                continue
            
            answers = StudentAnswer.objects.filter(student=student, question__quiz=quiz)
            total = quiz.questions.count()
            correct = answers.filter(is_correct=True).count()
            
            if total > 0 and (correct / total) < 0.6:
                weak_lessons.append(quiz.lesson)
        
        return list(set(weak_lessons))

    def select_revision_topics(self, student, course):
        """Select 3-5 topics based on recent lessons and weak topics."""
        recent_lessons = list(Lesson.objects.filter(course=course).order_by('-created_at')[:5])
        weak_lessons = self.get_weak_topics(student, course)
        
        # Combine and prioritize
        # Weighting: 50% weak, 50% recent
        # Since quiz is small, we just need a few topics for the prompt.
        selected_weak = weak_lessons[:3]
        selected_recent = [l for l in recent_lessons if l not in selected_weak][:3]
        
        all_selected = list(set(selected_weak + selected_recent))
        return all_selected[:5]

    def generate_revision_quiz(self, course, student=None):
        """Generates a revision quiz using Gemini 2.5 Flash."""
        if not self.api_key or not genai:
            raise Exception("Gemini API key not configured")

        if student:
            lessons = self.select_revision_topics(student, course)
        else:
            # Global assignment for the course (e.g. if instructor triggers)
            lessons = list(Lesson.objects.filter(course=course).order_by('-created_at')[:5])

        if not lessons:
            raise Exception("Insufficient lessons to generate a revision quiz.")

        topics_text = ", ".join([l.title for l in lessons])
        context_data = "\n\n".join([f"Topic: {l.title}\nContent: {l.content[:500]}" for l in lessons])

        prompt = f"""You are an educational AI assistant. Generate a MULTI-TOPIC revision quiz for the course '{course.title}'.
Cover the following topics: {topics_text}

The quiz MUST contain exactly:
- 3 multiple-choice questions (MCQ)
- 1 true/false question
- 1 short-answer question

Include correct answers and short explanations for each.

OUTPUT FORMAT MUST BE A VALID RAW JSON ARRAY ONLY WITH NO MARKDOWN DELIMITERS, NO BACKTICKS, JUST THE RAW JSON.
Format example:
[
  {{
    "question_type": "mcq",
    "question_text": "...",
    "options": ["A", "B", "C", "D"],
    "correct_answer": "...",
    "explanation": "..."
  }},
  ...
]

CONTEXT:
{context_data}
"""

        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            raw_text = response.text.strip()
            
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
            quiz_data = json.loads(raw_text.strip())
            
            # Create the Quiz instance
            title = f"Revision Quiz: {course.title} - {timezone.now().strftime('%b %d')}"
            quiz = Quiz.objects.create(
                course=course,
                title=title,
                is_published=True,
                is_revision=True
            )
            
            for q_data in quiz_data:
                Question.objects.create(
                    quiz=quiz,
                    question_type=q_data.get('question_type', 'mcq'),
                    question_text=q_data.get('question_text'),
                    options=q_data.get('options'),
                    correct_answer=q_data.get('correct_answer'),
                    explanation=q_data.get('explanation')
                )
            
            # Create RevisionQuiz record
            rev_quiz = RevisionQuiz.objects.create(
                course=course,
                quiz=quiz,
                title=title,
                topics_covered=topics_text
            )
            
            return rev_quiz
        except Exception as e:
            logger.error(f"Revision quiz generation error: {e}")
            raise Exception(f"Failed to generate revision quiz: {str(e)}")

    def trigger_batch_revision_quizzes(self):
        """Daily task implementation to check all courses and generate quizzes if needed."""
        courses = Course.objects.filter(auto_revision_enabled=True)
        count = 0
        
        for course in courses:
            if self.check_instructor_inactivity(course):
                try:
                    # Generate one quiz for the course (available to all students)
                    rev_quiz = self.generate_revision_quiz(course)
                    
                    # Notify students
                    from enrollments.models import Enrollment
                    students = Enrollment.objects.filter(batch__course=course, status='active').values_list('student', flat=True).distinct()
                    
                    for s_id in students:
                        user = User.objects.get(id=s_id)
                        notify_user(
                            user=user,
                            title="Revision Quiz Available",
                            message=f"No new lessons have been posted for the past two weeks. Try this revision quiz to review previous topics: {rev_quiz.topics_covered}",
                            n_type='QUIZ_REMINDER',
                            link=reverse('quizzes:take', kwargs={'quiz_id': rev_quiz.quiz.id})
                        )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to trigger revision quiz for {course.title}: {e}")
        
        return count
