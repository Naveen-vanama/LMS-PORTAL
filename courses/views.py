import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q

from .models import Course, Batch, Group, Announcement, Lesson
from .forms import CourseForm, BatchForm, GroupForm, AnnouncementForm, AIGeneratorForm, LessonForm
from enrollments.models import Enrollment

logger = logging.getLogger(__name__)


@login_required
def course_list(request):
    query = request.GET.get('q', '')
    courses = Course.objects.select_related('instructor').annotate(
        batch_count=Count('batches', distinct=True),
        student_count=Count('batches__enrollments', distinct=True),
    )
    if query:
        courses = courses.filter(
            Q(title__icontains=query) | Q(code__icontains=query) |
            Q(description__icontains=query)
        )
    # Students only see active courses
    if request.user.is_student:
        courses = courses.filter(status='active')
    return render(request, 'courses/course_list.html', {
        'courses': courses, 'query': query
    })


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    batches = course.batches.annotate(enrollment_count=Count('enrollments'))
    announcements = course.announcements.all()[:5]  # Latest 5
    
    student_enrolled_batch_ids = []
    progress = None
    
    if request.user.is_student:
        student_enrolled_batch_ids = list(
            Enrollment.objects.filter(student=request.user, batch__course=course)
            .exclude(status=Enrollment.Status.DROPPED)
            .values_list('batch_id', flat=True)
        )
        
        # Calculate progress
        from resources.models import FileResource, ResourceView
        relevant_resources = FileResource.objects.filter(
            course=course, is_visible=True
        ).filter(Q(batch__in=student_enrolled_batch_ids) | Q(batch__isnull=True))
        
        total_res = relevant_resources.count()
        if total_res > 0:
            viewed_count = ResourceView.objects.filter(
                student=request.user, resource__in=relevant_resources
            ).count()
            progress = round((viewed_count / total_res) * 100)

        enrollments = Enrollment.objects.filter(student=request.user, batch__course=course).select_related('certificate')
        
    lessons = course.lessons.all()
    
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'batches': batches,
        'announcements': announcements,
        'lessons': lessons,
        'student_enrolled_batch_ids': student_enrolled_batch_ids,
        'progress': progress,
        'enrollments': enrollments if request.user.is_student else [],
    })


@login_required
def course_create(request):
    if not (request.user.is_admin_role or request.user.is_superuser):
        messages.error(request, 'Permission denied.')
        return redirect('courses:list')
    form = CourseForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Course created successfully!')
        return redirect('courses:list')
    return render(request, 'courses/course_form.html', {'form': form, 'title': 'Create Course'})


@login_required
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if not (request.user.is_admin_role or request.user.is_superuser):
        messages.error(request, 'Permission denied.')
        return redirect('courses:detail', pk=pk)
    form = CourseForm(request.POST or None, request.FILES or None, instance=course)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Course updated successfully!')
        return redirect('courses:detail', pk=pk)
    return render(request, 'courses/course_form.html', {'form': form, 'title': 'Edit Course', 'course': course})


@login_required
def batch_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    if not (request.user.is_admin_role or request.user.is_superuser or
            request.user == course.instructor):
        messages.error(request, 'Permission denied.')
        return redirect('courses:detail', pk=course_pk)
    form = BatchForm(request.POST or None, initial={'course': course})
    if request.method == 'POST' and form.is_valid():
        batch = form.save(commit=False)
        batch.course = course
        batch.save()
        messages.success(request, 'Batch created successfully!')
        return redirect('courses:detail', pk=course_pk)
    return render(request, 'courses/batch_form.html', {
        'form': form, 'course': course, 'title': 'Create Batch'
    })


@login_required
def group_create(request, batch_pk):
    batch = get_object_or_404(Batch, pk=batch_pk)
    if not (request.user.is_admin_role or request.user.is_superuser or
            request.user == batch.course.instructor):
        messages.error(request, 'Permission denied.')
        return redirect('courses:detail', pk=batch.course_id)
    form = GroupForm(request.POST or None, batch=batch)
    if request.method == 'POST' and form.is_valid():
        group = form.save(commit=False)
        group.batch = batch
        group.save()
        form.save_m2m()
        messages.success(request, 'Group created successfully!')
        return redirect('courses:detail', pk=batch.course_id)
    return render(request, 'courses/group_form.html', {
        'form': form, 'batch': batch
    })


@login_required
def announcement_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    if not (request.user.is_admin_role or request.user.is_superuser or
            request.user == course.instructor):
        messages.error(request, 'Permission denied.')
        return redirect('courses:detail', pk=course_pk)
    
    from .forms import AnnouncementForm
    form = AnnouncementForm(request.POST or None, course=course)
    if request.method == 'POST' and form.is_valid():
        announcement = form.save(commit=False)
        announcement.course = course
        announcement.author = request.user
        announcement.save()
        messages.success(request, 'Announcement posted!')
        return redirect('courses:detail', pk=course_pk)
    
    return render(request, 'courses/announcement_form.html', {
        'form': form, 'course': course
    })


from .generator_service import ContentGeneratorService
from .forms import AIGeneratorForm, LessonForm
from django.core.files.storage import default_storage
import tempfile
import os

@login_required
def course_generator(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not (request.user.is_admin_role or request.user == course.instructor):
        messages.error(request, "Permission denied.")
        return redirect('courses:detail', pk=course.id)

    if request.method == 'POST':
        form = AIGeneratorForm(request.POST, request.FILES)
        if form.is_valid():
            topic = form.cleaned_data.get('topic')
            pdf_file = request.FILES.get('pdf_file')
            
            svc = ContentGeneratorService()
            pdf_text = None
            
            if pdf_file:
                # Save temp file for processing
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    for chunk in pdf_file.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name
                
                try:
                    pdf_text = svc.extract_and_chunk_pdf(tmp_path)
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
            
            try:
                content_data = svc.generate_lesson_content(topic=topic, pdf_text=pdf_text)
                # Store in session for preview
                request.session['gen_lesson_title'] = content_data.get('title')
                request.session['gen_lesson_content'] = f"## Explanation\n{content_data.get('explanation')}\n\n## Code Examples\n{content_data.get('code_examples')}\n\n## Key Concepts\n- " + "\n- ".join(content_data.get('key_concepts')) + f"\n\n## Summary\n{content_data.get('summary')}\n\n## Practice Exercises\n- " + "\n- ".join(content_data.get('practice_exercises'))
                
                return redirect('courses:generator_preview', course_id=course.id)
            except Exception as e:
                logger.error(f"Generation failed: {str(e)}", exc_info=True)
                messages.error(request, f"Generation failed: {str(e)}")
    else:
        form = AIGeneratorForm()

    return render(request, 'courses/generator_input.html', {
        'course': course,
        'form': form
    })

@login_required
def generator_preview(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not (request.user.is_admin_role or request.user == course.instructor):
        messages.error(request, "Permission denied.")
        return redirect('courses:detail', pk=course.id)

    title = request.session.get('gen_lesson_title')
    content = request.session.get('gen_lesson_content')

    if not title or not content:
        messages.warning(request, "No generated content found.")
        return redirect('courses:course_generator', course_id=course.id)

    if request.method == 'POST':
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            lesson.generated_by_ai = True
            lesson.save()
            
            # Now generate Quiz for this lesson
            try:
                from quizzes.models import Quiz, Question
                svc = ContentGeneratorService()
                quiz_questions = svc.generate_quiz_for_lesson(lesson.content)
                
                if quiz_questions:
                    quiz = Quiz.objects.create(
                        course=course,
                        lesson=lesson,
                        title=f"Quiz: {lesson.title}",
                        is_published=True
                    )
                    for q_data in quiz_questions:
                        Question.objects.create(
                            quiz=quiz,
                            question_type=q_data.get('question_type', 'mcq'),
                            question_text=q_data.get('question_text'),
                            options=q_data.get('options'),
                            correct_answer=q_data.get('correct_answer'),
                            explanation=q_data.get('explanation')
                        )
                    messages.success(request, f"Lesson published successfully with AI-generated quiz!")
                else:
                    messages.success(request, f"Lesson published successfully (Quiz generation skipped).")
            except Exception as e:
                messages.warning(request, f"Lesson published, but quiz generation failed: {str(e)}")
            
            # Clean session
            if 'gen_lesson_title' in request.session: del request.session['gen_lesson_title']
            if 'gen_lesson_content' in request.session: del request.session['gen_lesson_content']
            
            return redirect('courses:detail', pk=course.id)
    else:
        form = LessonForm(initial={'title': title, 'content': content})

    return render(request, 'courses/generator_preview.html', {
        'course': course,
        'form': form
    })
