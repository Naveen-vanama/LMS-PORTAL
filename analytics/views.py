from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from courses.models import Course
from .services import AnalyticsService

@login_required
def student_analytics_dashboard(request):
    if not request.user.is_student:
        return render(request, '403.html', status=403)
    
    analytics_data = AnalyticsService.get_student_analytics(request.user)
    return render(request, 'analytics/student_dashboard.html', {
        'analytics': analytics_data
    })

@login_required
def instructor_analytics_dashboard(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not (request.user.is_admin_role or request.user == course.instructor):
        return render(request, '403.html', status=403)
    
    analytics_data = AnalyticsService.get_instructor_analytics(course_id)
    return render(request, 'analytics/instructor_dashboard.html', {
        'course': course,
        'analytics': analytics_data
    })

@login_required
def api_student_analytics(request):
    if not request.user.is_student:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    data = AnalyticsService.get_student_analytics(request.user)
    return JsonResponse(data)

@login_required
def api_instructor_analytics(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not (request.user.is_admin_role or request.user == course.instructor):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    data = AnalyticsService.get_instructor_analytics(course_id)
    return JsonResponse(data)
