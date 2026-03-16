import os
import json
import logging
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)


class AssignmentGradingService:
    """
    Uses Gemini 2.5 Flash to auto-grade student assignment submissions.
    Returns a structured dict with score and detailed feedback.
    """

    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_API_KEY', os.environ.get('GOOGLE_API_KEY'))
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_name = 'gemini-2.5-flash'

    def grade_submission(self, assignment, submission):
        """
        Grade an AssignmentSubmission using Gemini AI.

        Returns:
            dict: {
                'score': float,
                'feedback': str,
                'suggestions': str,
                'correct_solution': str (optional)
            }
        """
        if not self.api_key:
            raise Exception("Gemini API key not configured.")

        assignment_type = assignment.assignment_type
        student_answer = submission.code_submission if assignment_type == 'coding' else submission.answer_text

        if not student_answer or student_answer.strip() == '':
            return {
                'score': 0,
                'feedback': 'No answer was submitted.',
                'suggestions': 'Please submit a valid answer.',
                'correct_solution': '',
            }

        if assignment_type == 'coding':
            prompt = self._build_coding_prompt(assignment, student_answer)
        else:
            prompt = self._build_text_prompt(assignment, student_answer)

        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            raw_text = response.text.strip()

            # Strip markdown code fences if present
            if raw_text.startswith('```json'):
                raw_text = raw_text[7:]
            if raw_text.startswith('```'):
                raw_text = raw_text[3:]
            if raw_text.endswith('```'):
                raw_text = raw_text[:-3]

            result = json.loads(raw_text.strip())
            # Clamp score to max_score
            max_score = float(assignment.max_score)
            raw_score = float(result.get('score', 0))
            clamped_score = min(max(raw_score, 0), max_score)
            result['score'] = round(clamped_score, 2)
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Grading JSON parse error: {e} — Raw: {response.text[:500]}")
            # Attempt to extract score from plain text
            return self._fallback_parse(response.text, assignment.max_score)
        except Exception as e:
            logger.error(f"Grading service error: {e}")
            raise Exception(f"AI grading failed: {str(e)}")

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def _build_coding_prompt(self, assignment, student_code):
        return f"""You are an expert programming instructor and evaluator.

Assignment Title: {assignment.title}
Assignment Description:
{assignment.description}

Student's Code Submission:
```
{student_code}
```

Evaluate the student's code based on:
1. Correctness — Does it solve the problem?
2. Efficiency — Is the algorithm/approach optimal?
3. Code Readability — Is it clean, well-named, formatted?
4. Best Practices — Error handling, edge cases, comments

Max Score: {assignment.max_score} points

Respond ONLY with a valid JSON object (no markdown, no extra text):
{{
  "score": <numeric score out of {assignment.max_score}>,
  "feedback": "<detailed feedback on correctness, efficiency, and style>",
  "suggestions": "<specific tips to improve the code>",
  "correct_solution": "<a clean reference solution with brief comments>"
}}"""

    def _build_text_prompt(self, assignment, student_answer):
        return f"""You are an expert instructor and evaluator.

Assignment Title: {assignment.title}
Assignment Description:
{assignment.description}

Student's Answer:
{student_answer}

Evaluate the student's answer based on:
1. Correctness — Is the answer factually correct?
2. Completeness — Does it cover all required points?
3. Clarity — Is it clearly written and well-structured?
4. Depth — Does it show understanding beyond surface level?

Max Score: {assignment.max_score} points

Respond ONLY with a valid JSON object (no markdown, no extra text):
{{
  "score": <numeric score out of {assignment.max_score}>,
  "feedback": "<detailed constructive feedback>",
  "suggestions": "<specific suggestions for improvement>",
  "correct_solution": "<a model answer or key points the student should have covered>"
}}"""

    def _fallback_parse(self, raw_text, max_score):
        """Last-resort parser if Gemini returns non-JSON."""
        import re
        score_match = re.search(r'score["\s:]*(\d+(?:\.\d+)?)', raw_text, re.IGNORECASE)
        score = float(score_match.group(1)) if score_match else 5.0
        score = min(max(score, 0), float(max_score))
        return {
            'score': round(score, 2),
            'feedback': raw_text[:1000],
            'suggestions': 'Review the feedback above for improvement areas.',
            'correct_solution': '',
        }
