import json
import os
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types


@dataclass
class HomeworkImage:
    mime_type: str
    data: bytes


class GeminiHomeworkService:
    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        self.client = genai.Client(api_key=self.api_key)

    def generate_socratic_hint(
        self,
        *,
        assignment_title: str,
        assignment_description: str,
        student_question: str,
        reference_answer_key: str | None = None,
        images: list[HomeworkImage] | None = None,
    ) -> str:
        system_prompt = (
            "You are a strict Socratic tutor for school homework.\n"
            "Rules:\n"
            "1) Never give final answers.\n"
            "2) Give only a guided hint and a next-step question.\n"
            "3) Be concise and age-appropriate.\n"
            "4) If image quality is poor, mention what to recapture."
        )
        user_prompt = (
            f"Assignment Title: {assignment_title}\n"
            f"Assignment Description: {assignment_description}\n"
            f"Reference Rubric/Answer Key (for tutor context only): {reference_answer_key or 'Not provided'}\n"
            f"Student Doubt: {student_question or 'No text question provided.'}\n"
            "Return plain text with:\n"
            "- Hint\n"
            "- Next question"
        )

        parts = [types.Part.from_text(text=user_prompt)]
        for image in images or []:
            parts.append(types.Part.from_bytes(data=image.data, mime_type=image.mime_type))

        response = self.client.models.generate_content(
            model=self.model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty hint response")
        return text

    def grade_submission(
        self,
        *,
        assignment_title: str,
        assignment_description: str,
        reference_answer_key: str | None,
        expected_time_minutes: int,
        active_duration_seconds: int,
        hints_used_count: int,
        images: list[HomeworkImage],
    ) -> dict[str, Any]:
        system_prompt = (
            "You are an expert homework evaluator.\n"
            "Evaluate handwritten work from notebook images against assignment instructions and rubric.\n"
            "Output strict JSON only."
        )
        user_prompt = (
            "Evaluate this submission and return JSON with the exact schema:\n"
            "{\n"
            '  "accuracy_score": number,  // 0 to 100\n'
            '  "overall_summary": string,\n'
            '  "step_by_step_review": [\n'
            "    {\n"
            '      "step": string,\n'
            '      "observation": string,\n'
            '      "is_correct": boolean,\n'
            '      "correction_hint": string\n'
            "    }\n"
            "  ],\n"
            '  "strengths": [string],\n'
            '  "areas_to_improve": [string],\n'
            '  "common_mistakes": [string]\n'
            "}\n\n"
            f"Assignment Title: {assignment_title}\n"
            f"Assignment Description: {assignment_description}\n"
            f"Reference Answer Key/Rubric: {reference_answer_key or 'Not provided'}\n"
            f"Expected Time (minutes): {expected_time_minutes}\n"
            f"Student Active Duration (seconds): {active_duration_seconds}\n"
            f"Hints Used Count: {hints_used_count}\n"
            "Now evaluate the provided notebook page images."
        )

        parts = [types.Part.from_text(text=user_prompt)]
        for image in images:
            parts.append(types.Part.from_bytes(data=image.data, mime_type=image.mime_type))

        response = self.client.models.generate_content(
            model=self.model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty grading response")

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Gemini grading response was not valid JSON") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("Gemini grading response JSON was not an object")
        return payload
