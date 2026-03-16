from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import os
import re
from django.db.models import Q

from .models import FileResource, ResourceView
from .forms import FileResourceForm
from courses.models import Course
from ai_assistant.services import RAGService, TextExtractor


@login_required
def resource_list(request, course_pk):
    """Lists all visible resources for a course, filtered by student batch if applicable."""
    course = get_object_or_404(Course, pk=course_pk)
    resources = FileResource.objects.filter(course=course, is_visible=True)
    viewed_ids = []
    if request.user.is_student:
        from enrollments.models import Enrollment
        enrolled_batch_ids = Enrollment.objects.filter(
            student=request.user, batch__course=course
        ).values_list('batch_id', flat=True)
        resources = resources.filter(
            Q(batch__in=enrolled_batch_ids) | Q(batch__isnull=True)
        )
        viewed_ids = list(ResourceView.objects.filter(student=request.user, resource__in=resources).values_list('resource_id', flat=True))

    return render(request, 'resources/resource_list.html', {
        'course': course, 'resources': resources, 'viewed_ids': viewed_ids
    })


@login_required
def resource_upload(request, course_pk):
    """Allows instructors and admins to upload new course resources."""
    course = get_object_or_404(Course, pk=course_pk)
    can_upload = (
        request.user == course.instructor or
        request.user.is_admin_role or
        request.user.is_superuser
    )
    if not can_upload:
        messages.error(request, 'Only instructors and admins can upload resources.')
        return redirect('resources:list', course_pk=course_pk)

    form = FileResourceForm(request.POST or None, request.FILES or None, course=course)
    if request.method == 'POST' and form.is_valid():
        resource = form.save(commit=False)
        resource.course = course
        resource.uploaded_by = request.user
        resource.save()

        # Extract and Index Content into RAG
        content_extracted = f"Resource Title: {resource.title}\nDescription: {resource.description}\n"
        if resource.file and resource.file.name.endswith('.pdf'):
            try:
                content_extracted += TextExtractor.extract_from_pdf(resource.file.path)
            except Exception as e:
                pass
        
        # Start indexing
        rag_svc = RAGService(course_id=course.id)
        rag_svc.process_course_material(content_extracted, metadata={'resource_id': resource.id})

        # Trigger Notifications for all enrolled students
        from notifications.services import notify_user
        from enrollments.models import Enrollment
        from django.urls import reverse
        
        # Only notify if it belongs to a batch or is course-wide
        students_to_notify = Enrollment.objects.filter(batch__course=course, status='active')
        if resource.batch:
            students_to_notify = students_to_notify.filter(batch=resource.batch)
        
        for enrollment in students_to_notify.select_related('student'):
            notify_user(
                user=enrollment.student,
                title="New Lesson Added",
                message=f"A new resource '{resource.title}' has been added to {course.code}.",
                n_type='NEW_LESSON',
                link=reverse('resources:list', kwargs={'course_pk': course.id})
            )
        
        messages.success(request, 'Resource uploaded and indexed successfully!')
        return redirect('resources:list', course_pk=course_pk)
    return render(request, 'resources/resource_form.html', {
        'form': form, 'course': course
    })


@login_required
def resource_delete(request, pk):
    """Deletes a resource after permission check."""
    resource = get_object_or_404(FileResource, pk=pk)
    course_pk = resource.course_id
    can_delete = (
        request.user == resource.uploaded_by or
        request.user.is_admin_role or
        request.user.is_superuser
    )
    if not can_delete:
        messages.error(request, 'Permission denied.')
    else:
        resource.delete()
        messages.success(request, 'Resource deleted.')
    return redirect('resources:list', course_pk=course_pk)


@login_required
def resource_view_track(request, pk):
    """Marks a resource as viewed and redirects to the file/link."""
    resource = get_object_or_404(FileResource, pk=pk)
    
    if request.user.is_student:
        ResourceView.objects.get_or_create(student=request.user, resource=resource)
    
    url = resource.file.url if resource.file else resource.external_url
    if not url:
        messages.error(request, "Resource has no file or URL.")
        return redirect('resources:list', course_pk=resource.course_id)
        
    return redirect(url)


@login_required
def resource_edit(request, pk):
    """Allows instructors and admins to edit existing resource details."""
    resource = get_object_or_404(FileResource, pk=pk)
    course = resource.course
    can_edit = (
        request.user == resource.uploaded_by or
        request.user.is_admin_role or
        request.user.is_superuser
    )
    if not can_edit:
        messages.error(request, 'Permission denied.')
        return redirect('resources:list', course_pk=course.pk)

    form = FileResourceForm(request.POST or None, request.FILES or None, instance=resource, course=course)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Resource updated!')
        return redirect('resources:list', course_pk=course.pk)
        
    return render(request, 'resources/resource_form.html', {
        'form': form, 'course': course, 'edit_mode': True
    })


@login_required
def resource_views_log(request, pk):
    """Provides a log of which students have viewed a specific resource."""
    resource = get_object_or_404(FileResource, pk=pk)
    course = resource.course
    if not (request.user == resource.uploaded_by or request.user.is_admin_role or request.user.is_superuser):
        messages.error(request, 'Permission denied.')
        return redirect('resources:list', course_pk=course.pk)
    
    views_log = resource.views.select_related('student').order_by('-viewed_at')
    return render(request, 'resources/resource_views_log.html', {
        'resource': resource, 'views_log': views_log
    })


@login_required
def resource_play(request, pk):
    """View to play/view a specific video resource with a custom player."""
    resource = get_object_or_404(FileResource, pk=pk)
    
    # Mark as viewed if student
    if request.user.is_student:
        ResourceView.objects.get_or_create(student=request.user, resource=resource)
        
    is_external = bool(resource.external_url and not resource.file)
    content_url = resource.file.url if resource.file else resource.external_url
    
    # Simple YouTube detector
    is_youtube = 'youtube.com' in content_url or 'youtu.be' in content_url
    yt_id = None
    if is_youtube:
        import re
        reg = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
        match = re.search(reg, content_url)
        if match:
            yt_id = match.group(1)

    return render(request, 'resources/resource_player.html', {
        'resource': resource,
        'content_url': content_url,
        'is_external': is_external,
        'is_youtube': is_youtube,
        'yt_id': yt_id
    })


@login_required
def serve_video(request, pk):
    """Serves video files with support for Range requests (required for seeking)."""
    resource = get_object_or_404(FileResource, pk=pk)
    if not resource.file:
        return redirect(resource.external_url)

    file_path = resource.file.path
    file_size = os.path.getsize(file_path)
    
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
    
    if range_match:
        first_byte, last_byte = range_match.groups()
        first_byte = int(first_byte) if first_byte else 0
        last_byte = int(last_byte) if last_byte else file_size - 1
        if last_byte >= file_size:
            last_byte = file_size - 1
        
        length = last_byte - first_byte + 1
        
        with open(file_path, 'rb') as f:
            f.seek(first_byte)
            content = f.read(length)
            
        from django.http import HttpResponse
        response = HttpResponse(content, status=206, content_type='video/mp4')
        response['Content-Range'] = f'bytes {first_byte}-{last_byte}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
        response['Content-Length'] = str(length)
        return response
    
    # Standard full-file response
    from django.http import FileResponse
    response = FileResponse(open(file_path, 'rb'), content_type='video/mp4')
    response['Accept-Ranges'] = 'bytes'
    return response
