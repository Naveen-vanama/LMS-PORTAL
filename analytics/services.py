import datetime
from django.db.models import Count, Avg, Sum, Q
from django.core.cache import cache
from django.utils import timezone
from courses.models import Course, Lesson
from quizzes.models import StudentAnswer, StudentStreak, Quiz
from enrollments.models import Enrollment
from certificates.models import Certificate
from .models import UserActivity

class AnalyticsService:
    @staticmethod
    def get_student_analytics(user):
        cache_key = f"student_analytics_{user.id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        enrollments = Enrollment.objects.filter(student=user)
        total_courses = enrollments.count()
        completed_courses = enrollments.filter(status=Enrollment.Status.COMPLETED).count()
        
        # Calculate overall progress
        total_progress = sum([e.progress for e in enrollments])
        avg_progress = round(total_progress / total_courses) if total_courses > 0 else 0

        # Quiz accuracy
        total_answers = StudentAnswer.objects.filter(student=user).count()
        correct_answers = StudentAnswer.objects.filter(student=user, is_correct=True).count()
        accuracy = round((correct_answers / total_answers) * 100) if total_answers > 0 else 0

        # Lessons Completed
        completed_lessons_count = 0
        for enrollment in enrollments:
             # Logic: if progress is 100%, consider all lessons completed for now
             # or we could use the many-to-many we added in UserActivity
             pass
        # Better: get distinct completed lessons from UserActivity
        completed_lessons_ids = UserActivity.objects.filter(user=user).values_list('lessons_completed', flat=True).distinct()
        completed_lessons_count = Lesson.objects.filter(id__in=completed_lessons_ids).count()

        # Streak
        streak_obj = getattr(user, 'streak', None)
        current_streak = streak_obj.current_streak if streak_obj else 0

        # Total Time Spent
        total_time_seconds = UserActivity.objects.filter(user=user).aggregate(total=Sum('time_spent_seconds'))['total'] or 0
        total_time_hours = round(total_time_seconds / 3600, 1)

        # Heatmap Data (Last 7 days)
        today = timezone.now().date()
        heatmap = []
        for i in range(6, -1, -1):
            date = today - datetime.timedelta(days=i)
            activity = UserActivity.objects.filter(user=user, activity_date=date).first()
            heatmap.append({
                'day': date.strftime('%a'),
                'date': date.isoformat(),
                'value': activity.time_spent_seconds // 60 if activity else 0 # minutes
            })

        # Daily Quiz Status
        from quizzes.models import DailyQuiz
        active_daily_quizzes = DailyQuiz.objects.filter(
            student=user,
            is_completed=False,
            expires_at__gt=timezone.now()
        ).select_related('course', 'quiz')

        daily_quizzes_info = []
        for dq in active_daily_quizzes:
            daily_quizzes_info.append({
                'course_id': dq.course.id,
                'course_title': dq.course.title,
                'topic': dq.topic_name,
                'questions_count': dq.quiz.questions.count(),
                'quiz_id': dq.quiz.id
            })
            
        # If no daily quiz exists, we can suggest starting one for their most active course
        startable_quizzes = []
        if not daily_quizzes_info:
            # Get latest active enrollment
            latest_enrollment = enrollments.filter(status=Enrollment.Status.ACTIVE).first()
            if latest_enrollment:
                startable_quizzes.append({
                    'course_id': latest_enrollment.batch.course.id,
                    'course_title': latest_enrollment.batch.course.title
                })

        # Revision Quizzes Status
        from quizzes.models import RevisionQuiz
        active_revision_quizzes = RevisionQuiz.objects.filter(
            course__batches__enrollments__student=user,
            course__batches__enrollments__status=Enrollment.Status.ACTIVE
        ).distinct().select_related('course', 'quiz')

        revision_quizzes_info = []
        for rq in active_revision_quizzes:
            # Check if student already took this revision quiz
            taken = StudentAnswer.objects.filter(student=user, question__quiz=rq.quiz).exists()
            if not taken:
                revision_quizzes_info.append({
                    'course_id': rq.course.id,
                    'course_title': rq.course.title,
                    'topics': rq.topics_covered,
                    'questions_count': rq.quiz.questions.count(),
                    'quiz_id': rq.quiz.id
                })

        data = {
            'avg_progress': avg_progress,
            'lessons_completed': completed_lessons_count,
            'quiz_accuracy': accuracy,
            'current_streak': current_streak,
            'total_time_learning': total_time_hours,
            'certificates_earned': Certificate.objects.filter(enrollment__student=user).count(),
            'heatmap': heatmap,
            'daily_quizzes': daily_quizzes_info,
            'startable_quizzes': startable_quizzes,
            'revision_quizzes': revision_quizzes_info
        }
        
        cache.set(cache_key, data, 3600) # Cache for 1 hour
        return data

    @staticmethod
    def get_instructor_analytics(course_id):
        course = Course.objects.get(id=course_id)
        cache_key = f"course_analytics_{course_id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        enrollments = Enrollment.objects.filter(batch__course=course)
        total_students = enrollments.values('student').distinct().count()
        
        completion_rate = 0
        if total_students > 0:
            completed = enrollments.filter(status=Enrollment.Status.COMPLETED).count()
            completion_rate = round((completed / total_students) * 100)

        # Average Quiz Score for this course
        quizzes = Quiz.objects.filter(course=course)
        avg_score = 0
        quiz_performances = []
        for quiz in quizzes:
            # For each quiz, calculate average score
            # A bit complex: (correct answers / total questions) per student, then average
            total_q = quiz.questions.count()
            if total_q > 0:
                answers = StudentAnswer.objects.filter(question__quiz=quiz)
                if answers.exists():
                    correct = answers.filter(is_correct=True).count()
                    total_attempts = answers.values('student').distinct().count()
                    if total_attempts > 0:
                        quiz_avg = (correct / (total_q * total_attempts)) * 100
                        quiz_performances.append({
                            'title': quiz.title,
                            'avg_score': round(quiz_avg),
                            'attempts': total_attempts
                        })

        if quiz_performances:
            avg_score = round(sum([p['avg_score'] for p in quiz_performances]) / len(quiz_performances))

        # Revenue
        total_revenue = sum([e.total_paid for e in enrollments])

        # Insights
        insights = []
        if quiz_performances:
            worst_quiz = min(quiz_performances, key=lambda x: x['avg_score'])
            if worst_quiz['avg_score'] < 50:
                insights.append(f"Quiz '{worst_quiz['title']}' has a high failure rate ({worst_quiz['avg_score']}% average score).")
            
            best_quiz = max(quiz_performances, key=lambda x: x['avg_score'])
            insights.append(f"Students are performing best in '{best_quiz['title']}'.")

        data = {
            'total_students': total_students,
            'completion_rate': completion_rate,
            'avg_quiz_score': avg_score,
            'total_revenue': float(total_revenue),
            'quiz_performances': quiz_performances,
            'insights': insights
        }

        cache.set(cache_key, data, 3600)
        return data
