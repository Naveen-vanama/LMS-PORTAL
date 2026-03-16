import os
import json
import logging
import google.generativeai as genai
from django.conf import settings
from ai_assistant.services import TextExtractor

logger = logging.getLogger(__name__)

class ContentGeneratorService:
    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_API_KEY', os.environ.get('GOOGLE_API_KEY'))
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_name = 'gemini-2.5-flash' 

    def generate_lesson_content(self, topic=None, pdf_text=None):
        """
        Generates structured course content from a topic or extracted PDF text.
        """
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        source_content = f"Topic: {topic}" if topic else f"Extracted Text from PDF: {pdf_text[:10000]}" # Limit text
        
        prompt = f"""You are a professional course content creator. Generate a structured lesson based on the following source:
{source_content}

The lesson MUST include:
1. Lesson Title
2. Lesson Explanation (comprehensive)
3. Code Examples (if applicable, else examples)
4. Key Concepts (bullet points)
5. Summary
6. Practice Exercises (at least 3)

OUTPUT FORMAT MUST BE A VALID JSON OBJECT ONLY. NO MARKDOWN, NO BACKTICKS.
Example Format:
{{
  "title": "Lesson Title",
  "explanation": "Detailed explanation here...",
  "code_examples": "```python\n# code here\n```",
  "key_concepts": ["Concept 1", "Concept 2"],
  "summary": "Quick summary here...",
  "practice_exercises": ["Ex 1", "Ex 2", "Ex 3"]
}}
"""

        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            raw_text = response.text.strip()
            
            # Clean possible markdown wrap
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
            content_data = json.loads(raw_text.strip())
            return content_data
        except Exception as e:
            logger.error(f"Content generation error: {e}")
            raise Exception(f"Failed to generate content: {str(e)}")

    def extract_and_chunk_pdf(self, pdf_file_path):
        """Extracts text from PDF using existing TextExtractor."""
        text = TextExtractor.extract_from_pdf(pdf_file_path)
        return text

    def generate_quiz_for_lesson(self, lesson_content):
        """Generates 3 MCQs and 2 short-answer questions for a lesson."""
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        prompt = f"""Based on the following lesson content, generate a quiz.
CONTENT:
{lesson_content}

The quiz MUST contain exactly:
- 3 multiple-choice questions (MCQ)
- 2 short-answer questions

OUTPUT FORMAT MUST BE A VALID RAW JSON ARRAY ONLY.
Format example:
[
  {{
    "question_type": "mcq",
    "question_text": "...",
    "options": ["A", "B", "C", "D"],
    "correct_answer": "...",
    "explanation": "..."
  }},
  {{
    "question_type": "short_answer",
    "question_text": "...",
    "options": null,
    "correct_answer": "...",
    "explanation": "..."
  }}
]
"""
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            raw_text = response.text.strip()
            
            # Clean possible markdown wrap
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
            return json.loads(raw_text.strip())
        except Exception as e:
            logger.error(f"Quiz generation error: {e}")
            return []
