from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Quiz, Question, StudentAnswer, DailyQuiz
from courses.models import Course
from enrollments.models import Enrollment
from .services import QuizGeneratorService, DailyQuizService
import json

@login_required
def generate_quiz(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not (request.user.is_admin_role or request.user == course.instructor):
        messages.error(request, "Permission denied.")
        return redirect('courses:detail', pk=course.id)

    try:
        svc = QuizGeneratorService(course.id)
        quiz_data = svc.generate_quiz_data()
        
        # Save to database
        quiz = Quiz.objects.create(
            course=course,
            title=f"AI Quiz: {course.code} - {timezone.now().strftime('%b %d, %Y')}",
            is_published=True
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
            
        # Trigger Notifications for all enrolled students
        from notifications.services import notify_user
        from enrollments.models import Enrollment
        from django.urls import reverse
        
        enrolled_students = Enrollment.objects.filter(batch__course=course, status='active').select_related('student')
        for enrollment in enrolled_students:
            notify_user(
                user=enrollment.student,
                title="New Quiz Available",
                message=f"An AI quiz has been generated for {course.code}. Challenge yourself!",
                n_type='QUIZ_REMINDER',
                link=reverse('quizzes:list', kwargs={'course_id': course.id})
            )
        
        messages.success(request, f"Generated and published quiz gracefully with {len(quiz_data)} questions!")
        return redirect('quizzes:list', course_id=course.id)
    except Exception as e:
        messages.error(request, f"Failed to generate quiz: {str(e)}")
        return redirect('courses:detail', pk=course.id)

@login_required
def quiz_list(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    quizzes = course.quizzes.filter(is_published=True).order_by('-created_at')
    
    # Simple check if enrolled (if student)
    if request.user.is_student:
        is_enrolled = Enrollment.objects.filter(student=request.user, batch__course=course).exists()
        if not is_enrolled:
            messages.error(request, "You are not enrolled in this course.")
            return redirect('courses:list')
            
    # For students, track if they have taken each quiz
    quiz_info = []
    for q in quizzes:
        taken = request.user.is_student and StudentAnswer.objects.filter(student=request.user, question__quiz=q).exists()
        quiz_info.append({
            'quiz': q,
            'taken': taken,
            'questions_count': q.questions.count()
        })
        
    return render(request, 'quizzes/quiz_list.html', {
        'course': course,
        'quiz_info': quiz_info
    })

@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    if request.user.is_student:
        is_enrolled = Enrollment.objects.filter(student=request.user, batch__course=quiz.course).exists()
        if not is_enrolled:
            messages.error(request, "You are not enrolled in this course.")
            return redirect('courses:list')
            
        if StudentAnswer.objects.filter(student=request.user, question__quiz=quiz).exists():
            messages.info(request, "You have already completed this quiz.")
            return redirect('quizzes:results', quiz_id=quiz.id)

    questions = quiz.questions.all()
    
    if request.method == 'POST':
        if not request.user.is_student:
            messages.warning(request, "Only students can submit answers.")
            return redirect('quizzes:list', course_id=quiz.course.id)
            
        svc = QuizGeneratorService(quiz.course.id)
        
        for question in questions:
            ans = request.POST.get(f"question_{question.id}", "").strip()
            
            is_correct = False
            if question.question_type == 'short_answer':
                is_correct = svc.grade_short_answer(question.question_text, question.correct_answer, ans)
            else:
                is_correct = (ans.lower() == question.correct_answer.lower())
                
            StudentAnswer.objects.create(
                student=request.user,
                question=question,
                selected_answer=ans,
                is_correct=is_correct
            )
        
        if quiz.is_daily:
            daily_quiz = DailyQuiz.objects.filter(student=request.user, quiz=quiz).first()
            if daily_quiz:
                daily_quiz.is_completed = True
                daily_quiz.save()

        from .streak_logic import update_daily_streak
        update_daily_streak(request.user)
        
        messages.success(request, "Quiz submitted successfully!")
        return redirect('quizzes:results', quiz_id=quiz.id)

    return render(request, 'quizzes/take_quiz.html', {
        'quiz': quiz,
        'questions': questions
    })

@login_required
def quiz_results(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    if request.user.is_student:
        answers = StudentAnswer.objects.filter(student=request.user, question__quiz=quiz).select_related('question')
        if not answers:
            messages.error(request, "You have not taken this quiz yet.")
            return redirect('quizzes:take', quiz_id=quiz.id)
            
        total = answers.count()
        correct = answers.filter(is_correct=True).count()
        
        return render(request, 'quizzes/quiz_results.html', {
            'quiz': quiz,
            'answers': answers,
            'score': correct,
            'total': total,
            'percentage': round((correct/total)*100) if total else 0
        })
        
    else:
        messages.info(request, "Instructors can view results in the admin panel or future results view.")
        return redirect('quizzes:list', course_id=quiz.course.id)

@login_required
def start_daily_quiz(request, course_id):
    if not request.user.is_student:
        messages.error(request, "Only students can take daily quizzes.")
        return redirect('courses:detail', pk=course_id)
        
    course = get_object_or_404(Course, id=course_id)
    is_enrolled = Enrollment.objects.filter(student=request.user, batch__course=course).exists()
    if not is_enrolled:
        messages.error(request, "You are not enrolled in this course.")
        return redirect('courses:list')
        
    try:
        svc = DailyQuizService(request.user, course)
        daily_quiz = svc.get_or_create_daily_quiz()
        return redirect('quizzes:take', quiz_id=daily_quiz.quiz.id)
    except Exception as e:
        messages.error(request, f"Failed to generate daily quiz: {str(e)}")
        return redirect('courses:detail', pk=course_id)

@login_required
def toggle_auto_revision(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not (request.user.is_admin_role or request.user == course.instructor):
        messages.error(request, "Permission denied.")
        return redirect('courses:detail', pk=course.id)
    
    course.auto_revision_enabled = not course.auto_revision_enabled
    course.save()
    
    status = "enabled" if course.auto_revision_enabled else "disabled"
    messages.success(request, f"Automatic revision quizzes {status} for {course.title}.")
    return redirect('courses:detail', pk=course.id)

@login_required
def manual_trigger_revision(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not (request.user.is_admin_role or request.user == course.instructor):
        messages.error(request, "Permission denied.")
        return redirect('courses:detail', pk=course.id)
    
    from .revision_service import RevisionQuizService
    try:
        svc = RevisionQuizService()
        rev_quiz = svc.generate_revision_quiz(course)
        messages.success(request, f"Revision quiz generated successfully: {rev_quiz.topics_covered}")
    except Exception as e:
        messages.error(request, f"Failed to generate revision quiz: {str(e)}")
        
    return redirect('quizzes:list', course_id=course.id)
@login_required
def edit_revision(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    if not (request.user.is_admin_role or request.user == quiz.course.instructor):
        messages.error(request, "Permission denied.")
        return redirect('courses:detail', pk=quiz.course.id)
    
    if request.method == 'POST':
        for question in quiz.questions.all():
            question.question_text = request.POST.get(f"q_{question.id}_text")
            question.correct_answer = request.POST.get(f"q_{question.id}_answer")
            question.explanation = request.POST.get(f"q_{question.id}_explanation")
            
            if question.question_type == 'mcq' or question.question_type == 'true_false':
                options = request.POST.getlist(f"q_{question.id}_options")
                question.options = [opt.strip() for opt in options if opt.strip()]
            
            question.save()
            
        messages.success(request, "Revision quiz updated successfully.")
        return redirect('quizzes:list', course_id=quiz.course.id)
        
    return render(request, 'quizzes/edit_revision.html', {
        'quiz': quiz,
        'questions': quiz.questions.all()
    })
