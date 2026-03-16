from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.db.models import Avg, Count
from .models import Assignment, AssignmentSubmission
from .forms import AssignmentSubmissionForm, InstructorReviewForm, AssignmentCreateForm
from .grading_service import AssignmentGradingService
from enrollments.models import Enrollment


# ──────────────────────────────────────────────────────────────
#  STUDENT VIEWS
# ──────────────────────────────────────────────────────────────

@login_required
def assignment_list(request, course_id):
    """List all assignments for a course."""
    from courses.models import Course
    course = get_object_or_404(Course, pk=course_id)

    # Security: only enrolled students & instructors/admins
    user = request.user
    if user.role not in ['instructor', 'admin']:
        enrolled = Enrollment.objects.filter(
            student=user,
            batch__course=course,
            status='active'
        ).exists()
        if not enrolled:
            return HttpResponseForbidden("You are not enrolled in this course.")

    assignments = Assignment.objects.filter(course=course).order_by('lesson__created_at', 'created_at')

    # Attach submission status for students
    submission_map = {}
    if user.role == 'student':
        for sub in AssignmentSubmission.objects.filter(student=user, assignment__course=course):
            submission_map[sub.assignment_id] = sub

    return render(request, 'assignments/assignment_list.html', {
        'course': course,
        'assignments': assignments,
        'submission_map': submission_map,
    })


@login_required
def assignment_detail(request, pk):
    """Show assignment details and submission form."""
    assignment = get_object_or_404(Assignment, pk=pk)
    user = request.user

    # Security: check enrollment (unless instructor/admin)
    if user.role not in ['instructor', 'admin']:
        enrolled = Enrollment.objects.filter(
            student=user,
            batch__course=assignment.course,
            status='active'
        ).exists()
        if not enrolled:
            return HttpResponseForbidden("You are not enrolled in this course.")

    # Check if already submitted
    existing_submission = AssignmentSubmission.objects.filter(
        student=user, assignment=assignment
    ).first()

    form = AssignmentSubmissionForm(assignment=assignment)

    return render(request, 'assignments/assignment_detail.html', {
        'assignment': assignment,
        'form': form,
        'existing_submission': existing_submission,
    })


@login_required
def submit_assignment(request, pk):
    """Handle student submission and trigger AI grading."""
    assignment = get_object_or_404(Assignment, pk=pk)
    user = request.user

    # Only students submit
    if user.role not in ['student']:
        return HttpResponseForbidden("Only students can submit assignments.")

    # Check enrollment
    enrolled = Enrollment.objects.filter(
        student=user,
        batch__course=assignment.course,
        status='active'
    ).exists()
    if not enrolled:
        return HttpResponseForbidden("You are not enrolled in this course.")

    # Prevent duplicate submissions
    if AssignmentSubmission.objects.filter(student=user, assignment=assignment).exists():
        messages.warning(request, "You have already submitted this assignment.")
        return redirect('assignments:result', pk=pk)

    if request.method == 'POST':
        form = AssignmentSubmissionForm(request.POST, assignment=assignment)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.student = user
            submission.assignment = assignment
            submission.save()

            # AI Grading
            try:
                grader = AssignmentGradingService()
                result = grader.grade_submission(assignment, submission)
                submission.ai_score = result.get('score', 0)
                feedback_parts = []
                if result.get('feedback'):
                    feedback_parts.append(result['feedback'])
                if result.get('suggestions'):
                    feedback_parts.append(f"\n💡 Suggestions:\n{result['suggestions']}")
                if result.get('correct_solution'):
                    feedback_parts.append(f"\n✅ Reference Solution:\n{result['correct_solution']}")
                submission.ai_feedback = "\n".join(feedback_parts)
                submission.graded_at = timezone.now()
                submission.save()
                messages.success(request, "Assignment submitted and graded successfully!")
            except Exception as e:
                messages.warning(request, f"Assignment submitted, but AI grading failed: {e}")

            return redirect('assignments:result', pk=pk)
    else:
        form = AssignmentSubmissionForm(assignment=assignment)

    return render(request, 'assignments/assignment_detail.html', {
        'assignment': assignment,
        'form': form,
        'existing_submission': None,
    })


@login_required
def assignment_result(request, pk):
    """Show the student's graded result."""
    assignment = get_object_or_404(Assignment, pk=pk)
    user = request.user

    submission = get_object_or_404(AssignmentSubmission, student=user, assignment=assignment)

    return render(request, 'assignments/assignment_result.html', {
        'assignment': assignment,
        'submission': submission,
    })


@login_required
def student_assignment_dashboard(request):
    """Student dashboard: all submitted assignments with scores."""
    user = request.user
    if user.role != 'student':
        return HttpResponseForbidden()

    submissions = AssignmentSubmission.objects.filter(
        student=user
    ).select_related('assignment', 'assignment__course').order_by('-submitted_at')

    return render(request, 'assignments/student_dashboard.html', {
        'submissions': submissions,
    })


# ──────────────────────────────────────────────────────────────
#  INSTRUCTOR VIEWS
# ──────────────────────────────────────────────────────────────

@login_required
def instructor_submissions(request, assignment_id):
    """Instructor view: all submissions for an assignment."""
    if request.user.role not in ['instructor', 'admin']:
        return HttpResponseForbidden()

    assignment = get_object_or_404(Assignment, pk=assignment_id)
    submissions = AssignmentSubmission.objects.filter(
        assignment=assignment
    ).select_related('student').order_by('-submitted_at')

    avg_score = submissions.aggregate(avg=Avg('ai_score'))['avg'] or 0

    return render(request, 'assignments/instructor_submissions.html', {
        'assignment': assignment,
        'submissions': submissions,
        'avg_score': round(avg_score, 2),
    })


@login_required
def instructor_review(request, submission_id):
    """Instructor manually overrides AI grading."""
    if request.user.role not in ['instructor', 'admin']:
        return HttpResponseForbidden()

    submission = get_object_or_404(AssignmentSubmission, pk=submission_id)

    if request.method == 'POST':
        form = InstructorReviewForm(request.POST, instance=submission)
        if form.is_valid():
            reviewed = form.save(commit=False)
            reviewed.graded_at = timezone.now()
            reviewed.save()
            messages.success(request, "Review saved successfully!")
            return redirect('assignments:instructor_submissions', assignment_id=submission.assignment.pk)
    else:
        form = InstructorReviewForm(instance=submission)

    return render(request, 'assignments/instructor_review.html', {
        'submission': submission,
        'form': form,
    })


@login_required
def instructor_dashboard(request):
    """Instructor view: all their assignments and stats."""
    if request.user.role not in ['instructor', 'admin']:
        return HttpResponseForbidden()

    assignments = Assignment.objects.filter(
        course__instructor=request.user
    ).annotate(
        submission_count=Count('submissions'),
        avg_score=Avg('submissions__ai_score')
    ).order_by('-created_at')

    return render(request, 'assignments/instructor_dashboard.html', {
        'assignments': assignments,
    })


@login_required
def create_assignment(request):
    """Instructor creates a new assignment."""
    if request.user.role not in ['instructor', 'admin']:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = AssignmentCreateForm(request.POST)
        if form.is_valid():
            assignment = form.save()
            messages.success(request, f"Assignment '{assignment.title}' created!")
            return redirect('assignments:instructor_dashboard')
    else:
        from courses.models import Course
        form = AssignmentCreateForm()
        # Limit courses to instructor's own courses
        form.fields['course'].queryset = request.user.courses_teaching.all()

    return render(request, 'assignments/create_assignment.html', {'form': form})
