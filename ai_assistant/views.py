from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ChatMessage
from .services import RAGService
from enrollments.models import Enrollment
from courses.models import Course

class AskAssistantView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        course_id = request.data.get('course_id')
        question = request.data.get('question')

        if not course_id or not question:
            return Response({'error': 'course_id and question are required'}, status=400)

        # Security: Prevent access to non-enrolled courses
        user = request.user
        if hasattr(user, 'role') and user.role == 'student':
            is_enrolled = Enrollment.objects.filter(student=user, batch__course_id=course_id).exists()
            if not is_enrolled:
                return Response({'error': 'You are not enrolled in this course.'}, status=403)

        # Call the RAG pipeline
        rag_svc = RAGService(course_id=course_id)
        answer = rag_svc.generate_answer(question)

        # Save chat directly to the database
        msg = ChatMessage.objects.create(
            student=user,
            course_id=course_id,
            question=question,
            answer=answer
        )

        return Response({
            'question': question,
            'answer': answer,
            'timestamp': msg.timestamp
        })

class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        # Enforce enrollment check here too if needed
        messages = ChatMessage.objects.filter(student=request.user, course_id=course_id).order_by('timestamp')
        data = [{
            'question': m.question,
            'answer': m.answer,
            'timestamp': m.timestamp
        } for m in messages]
        
        return Response({'history': data})

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import os
import tempfile
from .models import AITestLog
from .services import TextExtractor

@login_required
def ai_test_panel(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not (getattr(request.user, 'is_admin_role', False) or request.user == course.instructor):
        messages.error(request, "Permission denied. Only instructors can access the AI Test Panel.")
        return redirect('courses:detail', pk=course.id)

    debug_data = None
    if request.method == 'POST':
        action = request.POST.get('action')
        rag_svc = RAGService(course.id)
        
        if action == 'upload_pdf':
            pdf_file = request.FILES.get('pdf_file')
            if pdf_file and pdf_file.name.endswith('.pdf'):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    for chunk in pdf_file.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name
                
                try:
                    text = TextExtractor.extract_from_pdf(tmp_path)
                    if text:
                        rag_svc.process_course_material(text, metadata={'test_upload': True})
                        messages.success(request, "Document successfully indexed for AI assistant.")
                    else:
                        messages.error(request, "Could not extract text from PDF.")
                except Exception as e:
                    messages.error(request, f"Error processing PDF: {e}")
                finally:
                    os.unlink(tmp_path)
            else:
                messages.error(request, "Please upload a valid PDF file.")
                
        elif action == 'test_question':
            question = request.POST.get('question')
            if question:
                debug_data = rag_svc.test_rag_pipeline(question)
                
                if 'error' not in debug_data:
                    AITestLog.objects.create(
                        instructor=request.user,
                        course=course,
                        question=question,
                        retrieved_chunks=debug_data['retrieved_chunks'],
                        ai_response=debug_data['ai_response']
                    )

    recent_logs = AITestLog.objects.filter(course=course).order_by('-timestamp')[:5]

    return render(request, 'ai_assistant/ai_test_panel.html', {
        'course': course,
        'debug_data': debug_data,
        'recent_logs': recent_logs
    })
