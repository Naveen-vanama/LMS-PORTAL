from django.urls import path
from .views import AskAssistantView, ChatHistoryView, ai_test_panel

app_name = 'ai_assistant'

urlpatterns = [
    path('ask/', AskAssistantView.as_view(), name='ask_assistant'),
    path('history/<int:course_id>/', ChatHistoryView.as_view(), name='chat_history'),
    path('test-panel/<int:course_id>/', ai_test_panel, name='test_panel'),
]
