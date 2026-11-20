import base64
import json
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from google import genai

# (raw bytes, mime type) — e.g. (b"...", "image/png")
Image = Tuple[bytes, str]


class HomeworkGeminiService:
    @staticmethod
    def _get_client() -> genai.Client:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        return genai.Client(api_key=api_key)

    @staticmethod
    def _image_parts(images: Sequence[Image]) -> List[Dict[str, Any]]:
        """Inline image parts, each sent with its real type (it used to be hard-coded to JPEG)."""
        return [
            {"inline_data": {"mime_type": mime or "image/jpeg", "data": base64.b64encode(raw).decode("utf-8")}}
            for raw, mime in images
        ]

    @classmethod
    def generate_socratic_hint(
        cls,
        assignment_title: str,
        assignment_description: str,
        student_doubt: str,
        student_images: Optional[Sequence[Image]] = None,
        instruction_images: Optional[Sequence[Image]] = None,
    ) -> str:
        client = cls._get_client()
        prompt = (
            "You are a strict Socratic tutor for school homework.\n"
            "Never provide the final direct answer.\n"
            "Give a concise hint in 3-6 bullets that helps the student progress.\n\n"
            f"Homework: {assignment_title}\n"
            f"Instructions: {assignment_description or '(see the homework photos)'}\n"
            f"Student question: {student_doubt}"
        )
        parts: List[Any] = [prompt]
        if instruction_images:
            parts.append("Homework photos (the questions, e.g. a photo of the board):")
            parts.extend(cls._image_parts(instruction_images))
        if student_images:
            parts.append("Student's work so far:")
            parts.extend(cls._image_parts(student_images))

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=parts,
        )
        return (response.text or "Try solving one step at a time and verify each intermediate value.").strip()

    @classmethod
    def extract_instructions(cls, images: Sequence[Image], subject: str = "") -> str:
        """Draft homework instructions from photos (e.g. of the board) for the teacher to edit."""
        client = cls._get_client()
        prompt = (
            "These photos show school homework written on a board or a page.\n"
            "Write out the homework exactly as given, as clear plain-text instructions for students:\n"
            "- keep every question, number and formula; number the questions\n"
            "- do not solve anything and do not add your own questions\n"
            "- if part of the photo is unreadable, write [unclear] there\n"
            f"Subject: {subject or 'not given'}"
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, *cls._image_parts(images)],
        )
        return (response.text or "").strip()

    @classmethod
    def grade_submission(
        cls,
        assignment: Dict[str, Any],
        images: Sequence[Image],
        active_duration_seconds: int,
        hints_used_count: int,
        instruction_images: Optional[Sequence[Image]] = None,
        start_image: Optional[Image] = None,
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
                **({
                    "page_blank_at_start": {"type": "boolean"},
                    "same_page_as_start": {"type": "boolean"},
                    "page_check_notes": {"type": "string"},
                } if start_image else {}),
            },
            "required": [
                *(["page_blank_at_start", "same_page_as_start", "page_check_notes"] if start_image else []),
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
            "Use the homework description and optional reference answer key/rubric.\n"
            "Score strictness: 0-100 accuracy.\n"
            "Return only JSON matching schema.\n\n"
            f"Title: {assignment['title']}\n"
            f"Subject: {assignment['subject']}\n"
            f"Description: {assignment['description'] or '(see the homework photos)'}\n"
            f"Reference key: {assignment.get('reference_answer_key') or 'Not provided'}\n"
            f"Expected time (minutes): {assignment['expected_time_minutes']}\n"
            f"Active duration seconds: {active_duration_seconds}\n"
            f"Hints used count: {hints_used_count}\n"
        )

        parts: List[Any] = [prompt]
        if instruction_images:
            parts.append("Homework photos (the questions, e.g. a photo of the board):")
            parts.extend(cls._image_parts(instruction_images))
        if start_image:
            parts.append(
                "Page check. The next photo was taken when the student STARTED: it should show the notebook page "
                "blank apart from a printed QR sticker. Then come the finished pages; one of them carries the same "
                "QR sticker. Set page_blank_at_start=false if the start photo already shows answers or writing for "
                "this homework. Set same_page_as_start=false if the finished page with the QR sticker does not look "
                "like the same physical page (different paper, ruling, sticker position or notebook). Explain briefly "
                "in page_check_notes. These checks don't change the accuracy score."
            )
            parts.append("Start photo (blank page with QR sticker):")
            parts.extend(cls._image_parts([start_image]))
        parts.append("Student's notebook pages:")
        parts.extend(cls._image_parts(images))

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
