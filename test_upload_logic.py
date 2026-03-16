import os
import django
from django.test import RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from live_classes.views import upload_recording
from live_classes.models import LiveClass

User = get_user_model()

def test_upload():
    # 1. Setup data
    admin = User.objects.get(username='admin')
    live_class = LiveClass.objects.get(id=1) # Mastering Loops
    
    # 2. Create request
    factory = RequestFactory()
    file_content = b"dummy video content"
    video_file = SimpleUploadedFile("test_video.mp4", file_content, content_type="video/mp4")
    
    request = factory.post(f'/live-classes/upload/{live_class.id}/', {'recording': video_file})
    request.user = admin
    
    # Add message support
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    
    # 3. Call view
    response = upload_recording(request, live_class.id)
    
    # 4. Assert
    live_class.refresh_from_db()
    if live_class.recording_url:
        print(f"SUCCESS: Recording uploaded. Path: {live_class.recording_url.path}")
        # Clean up
        if os.path.exists(live_class.recording_url.path):
            os.remove(live_class.recording_url.path)
            print("Cleaned up test file.")
    else:
        print("FAILED: Recording URL is empty.")

if __name__ == "__main__":
    test_upload()
