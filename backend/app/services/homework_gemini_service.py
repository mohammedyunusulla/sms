import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Sequence, Tuple

from google import genai

# (raw bytes, mime type) — e.g. (b"...", "image/png")
Image = Tuple[bytes, str]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.1-pro-preview")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-4.1-mini")
AZURE_OPENAI_API_URL = os.getenv("AZURE_OPENAI_API_URL", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.2-90b-vision-preview")
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
CLOUDFLARE_MODEL = os.getenv("CLOUDFLARE_MODEL", "@cf/meta/llama-3.2-90b-vision-instruct")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
_cloudflare_api_url = os.getenv("CLOUDFLARE_API_URL")
CLOUDFLARE_API_URL = _cloudflare_api_url or (
    f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1/chat/completions"
    if CLOUDFLARE_ACCOUNT_ID
    else ""
)
AI_PROVIDER_ORDER = os.getenv("AI_PROVIDER_ORDER", "azure,groq,gemini,cloudflare")


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
    def _gemini_generate_text(cls, parts: List[Any], config: Optional[Dict[str, Any]] = None) -> str:
        """Try Gemini primary model, then optional Gemini fallback model."""
        client = cls._get_client()
        last_error: Optional[Exception] = None
        seen_models = set()
        for model in [GEMINI_MODEL, GEMINI_FALLBACK_MODEL]:
            if not model:
                continue
            if model in seen_models:
                continue
            seen_models.add(model)
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=parts,
                    config=config,
                )
                return (response.text or "").strip()
            except Exception as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise RuntimeError("No Gemini model is configured")

    @staticmethod
    def _parts_to_groq_content(parts: List[Any]) -> List[Dict[str, Any]]:
        content: List[Dict[str, Any]] = []
        for part in parts:
            if isinstance(part, str):
                content.append({"type": "text", "text": part})
                continue
            if isinstance(part, dict) and "inline_data" in part:
                inline = part.get("inline_data") or {}
                mime = inline.get("mime_type") or "image/jpeg"
                data = inline.get("data") or ""
                if data:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{data}"},
                    })
        return content

    @classmethod
    def _parts_to_responses_input_content(cls, parts: List[Any]) -> List[Dict[str, Any]]:
        content: List[Dict[str, Any]] = []
        for part in parts:
            if isinstance(part, str):
                content.append({"type": "input_text", "text": part})
                continue
            if isinstance(part, dict) and "inline_data" in part:
                inline = part.get("inline_data") or {}
                mime = inline.get("mime_type") or "image/jpeg"
                data = inline.get("data") or ""
                if data:
                    content.append({"type": "input_image", "image_url": f"data:{mime};base64,{data}"})
        return content

    @classmethod
    def _openai_compatible_generate_text(
        cls,
        *,
        api_url: str,
        api_key: str,
        model: str,
        provider_name: str,
        parts: List[Any],
        json_mode: bool = False,
    ) -> str:
        if not api_url:
            raise ValueError(f"{provider_name}_API_URL is not configured")
        if not api_key:
            raise ValueError(f"{provider_name}_API_KEY is not configured")
        if not model:
            raise ValueError(f"{provider_name}_MODEL is not configured")

        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "user", "content": cls._parts_to_groq_content(parts)}
            ],
            "temperature": 0.2,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore") if exc.fp else str(exc)
            raise RuntimeError(f"{provider_name} API error: {detail}") from exc

        parsed = json.loads(body or "{}")
        return (
            parsed.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

    @classmethod
    def _azure_openai_generate_text(cls, parts: List[Any], json_mode: bool = False) -> str:
        api_key = os.getenv("AZURE_OPENAI_API_KEY") or ""
        if not AZURE_OPENAI_API_URL:
            raise ValueError("AZURE_OPENAI_API_URL is not configured")
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY is not configured")
        if not AZURE_OPENAI_MODEL:
            raise ValueError("AZURE_OPENAI_MODEL is not configured")

        payload: Dict[str, Any] = {
            "model": AZURE_OPENAI_MODEL,
            "input": [
                {
                    "role": "user",
                    "content": cls._parts_to_responses_input_content(parts),
                }
            ],
            "temperature": 0.2,
        }
        if json_mode:
            payload["text"] = {"format": {"type": "json_object"}}

        req = urllib.request.Request(
            AZURE_OPENAI_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "api-key": api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore") if exc.fp else str(exc)
            raise RuntimeError(f"AZURE_OPENAI API error: {detail}") from exc

        parsed = json.loads(body or "{}")
        output_text = (parsed.get("output_text") or "").strip()
        if output_text:
            return output_text

        for item in parsed.get("output", []):
            for content_item in item.get("content", []):
                if content_item.get("type") == "output_text":
                    text = (content_item.get("text") or "").strip()
                    if text:
                        return text
        return ""

    @classmethod
    def _groq_generate_text(cls, parts: List[Any], json_mode: bool = False) -> str:
        api_key = os.getenv("GROQ_API_KEY")
        return cls._openai_compatible_generate_text(
            api_url=GROQ_API_URL,
            api_key=api_key or "",
            model=GROQ_MODEL,
            provider_name="GROQ",
            parts=parts,
            json_mode=json_mode,
        )

    @classmethod
    def _cloudflare_generate_text(cls, parts: List[Any], json_mode: bool = False) -> str:
        return cls._openai_compatible_generate_text(
            api_url=CLOUDFLARE_API_URL,
            api_key=CLOUDFLARE_API_TOKEN,
            model=CLOUDFLARE_MODEL,
            provider_name="CLOUDFLARE",
            parts=parts,
            json_mode=json_mode,
        )

    @classmethod
    def _generate_text(cls, parts: List[Any], config: Optional[Dict[str, Any]] = None, json_mode: bool = False) -> str:
        """Provider chain: azure -> groq -> gemini -> cloudflare (configurable via AI_PROVIDER_ORDER)."""
        errors: List[str] = []
        providers = [p.strip().lower() for p in AI_PROVIDER_ORDER.split(",") if p.strip()]
        if not providers:
            providers = ["azure", "groq", "gemini", "cloudflare"]

        for provider in providers:
            try:
                if provider == "azure":
                    return cls._azure_openai_generate_text(parts, json_mode=json_mode)
                if provider == "groq":
                    return cls._groq_generate_text(parts, json_mode=json_mode)
                if provider == "gemini":
                    return cls._gemini_generate_text(parts, config=config)
                if provider == "cloudflare":
                    return cls._cloudflare_generate_text(parts, json_mode=json_mode)
                errors.append(f"unknown provider '{provider}'")
            except Exception as exc:
                errors.append(f"{provider}: {exc}")
                continue

        raise RuntimeError("All AI providers failed: " + " | ".join(errors))

    @classmethod
    def generate_socratic_hint(
        cls,
        assignment_title: str,
        assignment_description: str,
        student_doubt: str,
        student_images: Optional[Sequence[Image]] = None,
        instruction_images: Optional[Sequence[Image]] = None,
    ) -> str:
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

        text = cls._generate_text(parts)
        return text or "Try solving one step at a time and verify each intermediate value."

    @classmethod
    def extract_instructions(cls, images: Sequence[Image], subject: str = "") -> str:
        """Draft homework instructions from photos (e.g. of the board) for the teacher to edit."""
        prompt = (
            "These photos show school homework written on a board or a page.\n"
            "Write out the homework exactly as given, as clear plain-text instructions for students:\n"
            "- keep every question, number and formula; number the questions\n"
            "- do not solve anything and do not add your own questions\n"
            "- if part of the photo is unreadable, write [unclear] there\n"
            f"Subject: {subject or 'not given'}"
        )
        return cls._generate_text([prompt, *cls._image_parts(images)])

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
        required_keys = [
            "accuracy_score",
            "line_by_line_review",
            "strengths",
            "areas_to_improve",
            "common_mistakes",
            "overall_feedback",
        ]
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
                *required_keys,
            ],
        }

        page_check_requirements = (
            "- page_blank_at_start: boolean\n"
            "- same_page_as_start: boolean\n"
            "- page_check_notes: string\n"
            if start_image
            else ""
        )

        prompt = (
            "Evaluate this student homework from notebook images.\n"
            "Use the homework description and optional reference answer key/rubric.\n"
            "Score strictness: 0-100 accuracy.\n"
            "Return only JSON matching schema.\n\n"
            "JSON requirements:\n"
            "- accuracy_score: number (0 to 100)\n"
            "- line_by_line_review: array of strings\n"
            "- strengths: array of strings\n"
            "- areas_to_improve: array of strings\n"
            "- common_mistakes: array of strings\n"
            "- overall_feedback: string\n"
            f"{page_check_requirements}\n"
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

        response_text = cls._generate_text(
            parts,
            config={
                "response_mime_type": "application/json",
                "response_schema": grading_schema,
            },
            json_mode=True,
        )
        parsed = json.loads(response_text or "{}")
        missing = [key for key in required_keys if key not in parsed]
        if missing:
            raise ValueError(f"Incomplete grading response; missing fields: {', '.join(missing)}")
        for key in ("line_by_line_review", "strengths", "areas_to_improve", "common_mistakes"):
            value = parsed.get(key)
            if not isinstance(value, list):
                parsed[key] = []
            else:
                parsed[key] = [str(item) for item in value if str(item).strip()]
        parsed["accuracy_score"] = float(parsed.get("accuracy_score", 0))
        if "overall_summary" not in parsed and "overall_feedback" in parsed:
            parsed["overall_summary"] = parsed["overall_feedback"]
        return parsed
