import os
import json
import logging
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from ai_assistant.models import CourseContentChunk
from ai_assistant.services import EmbeddingService, FAISSVectorStore

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


class QuizGeneratorService:
    def __init__(self, course_id):
        self.course_id = course_id
        self.api_key = getattr(settings, 'GOOGLE_API_KEY', os.environ.get('GOOGLE_API_KEY'))
        if self.api_key and genai:
            genai.configure(api_key=self.api_key)

    def generate_quiz_data(self):
        if not self.api_key or not genai:
            raise Exception("Gemini API key not configured")

        # 1. We need relevant chunks.
        query = "Core concepts, essential definitions, and important principles of the course"
        
        embedder = EmbeddingService()
        query_embedding = embedder.get_embedding(query)
        
        vector_store = FAISSVectorStore(self.course_id)
        relevant_chunks = vector_store.search(query_embedding, k=5)
        
        if not relevant_chunks:
            chunks_qs = CourseContentChunk.objects.filter(course_id=self.course_id).order_by('?')[:5]
            context_texts = [c.chunk_text for c in chunks_qs]
        else:
            context_texts = [c.chunk_text for c in relevant_chunks]
            
        context = "\n\n---\n\n".join(context_texts)
        if not context:
            raise Exception("No course materials indexed to generate a quiz from.")

        prompt = f"""You are an educational AI assistant. Based ONLY on the provided course materials, generate a comprehensive quiz.
The quiz MUST contain exactly:
- 5 multiple-choice questions (MCQ)
- 3 short-answer questions
- 2 true/false questions

OUTPUT FORMAT MUST BE A VALID RAW JSON ARRAY ONLY WITH NO MARKDOWN DELIMITERS, NO BACKTICKS, JUST THE RAW JSON.
Format example:
[
  {{
    "question_type": "mcq",
    "question_text": "...",
    "options": ["A", "B", "C", "D"],
    "correct_answer": "...",
    "explanation": "..."
  }}
]

COURSE MATERIALS CONTEXT:
{context}
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
            return quiz_data
        except Exception as e:
            logger.error(f"Quiz generation error: {e}")
            raise Exception("Failed to generate quiz from AI. Please try again.")

    def grade_short_answer(self, question_text, expected_answer, student_answer):
        """Uses Gemini to evaluate similarity/correctness of a short answer."""
        if not self.api_key or not genai:
            return False
            
        prompt = f"""You are an AI grading assistant. 
Question: {question_text}
Expected Correct Answer: {expected_answer}

Student Answer: {student_answer}

Evaluate if the student's answer is conceptually correct based on the expected answer. 
Respond with EXACTLY "CORRECT" or "INCORRECT", nothing else."""
        
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            verdict = response.text.strip().upper()
            return "CORRECT" in verdict
        except:
            return False


class DailyQuizService:
    def __init__(self, student, course):
        self.student = student
        self.course = course
        self.api_key = getattr(settings, 'GOOGLE_API_KEY', os.environ.get('GOOGLE_API_KEY'))
        if self.api_key and genai:
            genai.configure(api_key=self.api_key)

    def select_topic(self):
        """
        Logic:
        1. Check for new lessons (last 48 hours).
        2. Weak Topic Reinforcement (score < 60%).
        3. Previously studied topics (completed lessons).
        4. Fallback: Any lesson or course title.
        """
        from courses.models import Lesson
        from .models import StudentAnswer, Quiz
        
        # 1. New lessons (last 48 hours)
        recent_lessons = Lesson.objects.filter(
            course=self.course, 
            created_at__gte=timezone.now() - timedelta(days=2)
        ).order_by('-created_at')
        
        if recent_lessons.exists():
            lesson = recent_lessons.first()
            return lesson, lesson.title, False

        # 2. Weak Topic Reinforcement
        quizzes_taken = Quiz.objects.filter(
            course=self.course, 
            questions__student_answers__student=self.student
        ).distinct()
        
        for q in quizzes_taken:
            ans = StudentAnswer.objects.filter(student=self.student, question__quiz=q)
            total = q.questions.count()
            correct = ans.filter(is_correct=True).count()
            if total > 0 and (correct / total) < 0.6:
                topic_name = f"{q.lesson.title if q.lesson else 'Review'} (Review Quiz)"
                return q.lesson, topic_name, True

        # 3. Previously studied topics
        activity_lessons = Lesson.objects.filter(
            useractivity__user=self.student,
            course=self.course
        ).distinct().order_by('?')
        
        if activity_lessons.exists():
            lesson = activity_lessons.first()
            return lesson, lesson.title, False

        # 4. Fallback logic
        any_lesson = Lesson.objects.filter(course=self.course).order_by('?').first()
        if any_lesson:
            return any_lesson, any_lesson.title, False
            
        return None, f"{self.course.title} Basics", False

    def generate_daily_quiz(self):
        if not self.api_key or not genai:
            raise Exception("Gemini API key not configured")

        lesson, topic_name, is_review = self.select_topic()
        
        context = ""
        if lesson:
            context = f"Lesson Title: {lesson.title}\nLesson Content: {lesson.content[:2000]}"
        else:
            context = f"Course Title: {self.course.title}\nDescription: {self.course.description[:1000]}"

        prompt = f"""You are an educational AI assistant. Generate 5 quiz questions to review the topic '{topic_name}'.
The quiz MUST contain exactly:
- 3 multiple-choice questions (MCQ)
- 1 true/false question
- 1 short-answer question

Include both multiple choice and true/false questions as requested.

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
{context}
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
            return quiz_data, lesson, topic_name
        except Exception as e:
            logger.error(f"Daily quiz generation error: {e}")
            raise Exception("Failed to generate daily quiz from AI.")

    def get_or_create_daily_quiz(self):
        from .models import DailyQuiz, Quiz, Question
        
        # Check if active daily quiz exists for today
        existing = DailyQuiz.objects.filter(
            student=self.student, 
            course=self.course,
            expires_at__gt=timezone.now(),
            is_completed=False
        ).first()
        
        if existing:
            return existing

        # Generate new one
        quiz_data, lesson, topic_name = self.generate_daily_quiz()
        
        # Create Quiz instance
        quiz = Quiz.objects.create(
            course=self.course,
            lesson=lesson,
            title=f"Daily Quiz: {topic_name}",
            is_published=True,
            is_daily=True
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
            
        daily_quiz = DailyQuiz.objects.create(
            student=self.student,
            course=self.course,
            quiz=quiz,
            topic_name=topic_name,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        return daily_quiz
