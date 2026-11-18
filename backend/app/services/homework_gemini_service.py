import base64
import json
import os
from typing import Any, Dict, List, Optional

from google import genai


class HomeworkGeminiService:
    @staticmethod
    def _get_client() -> genai.Client:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        return genai.Client(api_key=api_key)

    @classmethod
    def generate_socratic_hint(
        cls,
        assignment_title: str,
        assignment_description: str,
        student_doubt: str,
        image_bytes: Optional[bytes] = None,
    ) -> str:
        client = cls._get_client()
        prompt = (
            "You are a strict Socratic tutor for school homework.\n"
            "Never provide the final direct answer.\n"
            "Give a concise hint in 3-6 bullets that helps the student progress.\n\n"
            f"Assignment: {assignment_title}\n"
            f"Instructions: {assignment_description}\n"
            f"Student question: {student_doubt}"
        )
        parts: List[Any] = [prompt]
        if image_bytes:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(image_bytes).decode("utf-8"),
                    }
                }
            )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=parts,
        )
        return (response.text or "Try solving one step at a time and verify each intermediate value.").strip()

    @classmethod
    def grade_submission(
        cls,
        assignment: Dict[str, Any],
        image_bytes_list: List[bytes],
        active_duration_seconds: int,
        hints_used_count: int,
    ) -> Dict[str, Any]:
        client = cls._get_client()
        grading_schema = {
            "type": "object",
            "properties": {
                "accuracy_score": {"type": "number"},
                "line_by_line_review": {"type": "array", "items": {"type": "string"}},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "areas_to_improve": {"type": "array", "items": {"type": "string"}},
                "common_mistakes": {"type": "array", "items": {"type": "string"}},
                "overall_feedback": {"type": "string"},
            },
            "required": [
                "accuracy_score",
                "line_by_line_review",
                "strengths",
                "areas_to_improve",
                "common_mistakes",
                "overall_feedback",
            ],
        }

        prompt = (
            "Evaluate this student homework from notebook images.\n"
            "Use the assignment description and optional reference answer key/rubric.\n"
            "Score strictness: 0-100 accuracy.\n"
            "Return only JSON matching schema.\n\n"
            f"Title: {assignment['title']}\n"
            f"Subject: {assignment['subject']}\n"
            f"Description: {assignment['description']}\n"
            f"Reference key: {assignment.get('reference_answer_key') or 'Not provided'}\n"
            f"Expected time (minutes): {assignment['expected_time_minutes']}\n"
            f"Active duration seconds: {active_duration_seconds}\n"
            f"Hints used count: {hints_used_count}\n"
        )

        parts: List[Any] = [prompt]
        for raw in image_bytes_list:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(raw).decode("utf-8"),
                    }
                }
            )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=parts,
            config={
                "response_mime_type": "application/json",
                "response_schema": grading_schema,
            },
        )
        parsed = json.loads(response.text or "{}")
        parsed["accuracy_score"] = float(parsed.get("accuracy_score", 0))
        if "overall_summary" not in parsed and "overall_feedback" in parsed:
            parsed["overall_summary"] = parsed["overall_feedback"]
        return parsed
