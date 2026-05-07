from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from minutes.config import Settings, get_settings


class OpenAICompatibleSummaryError(RuntimeError):
    """Raised when the summary backend returns an invalid or failed response."""


@dataclass(slots=True)
class SummaryResult:
    text: str
    structured_data: dict[str, list[str] | str]
    model_name: str
    base_url: str
    prompt_version: str
    summary_language: str


class OpenAICompatibleSummarizer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = OpenAI(
            api_key=self.settings.summary_api_key or "not-needed",
            base_url=self.settings.summary_base_url,
            timeout=float(self.settings.summary_timeout_seconds),
        )

    def summarize_text(self, text: str, summary_language: str) -> SummaryResult:
        content = text.strip()
        if not content:
            raise OpenAICompatibleSummaryError("Summary input text is empty.")
        if not self.settings.summary_configured:
            raise OpenAICompatibleSummaryError("Summary backend is not configured.")

        payload = {
            "model": self.settings.summary_model,
            "temperature": self.settings.summary_temperature,
            "messages": [
                {
                    "role": "system",
                    "content": self._system_prompt(summary_language),
                },
                {
                    "role": "user",
                    "content": self._user_prompt(content),
                },
            ],
        }

        response_payload = self._post_json(payload)
        raw_content = self._extract_content(response_payload)
        structured_data = self._parse_json_content(raw_content)
        return SummaryResult(
            text=self.render_text(structured_data),
            structured_data=structured_data,
            model_name=self.settings.summary_model or "unknown",
            base_url=self.settings.summary_base_url or "",
            prompt_version=self.settings.summary_prompt_version,
            summary_language=summary_language,
        )

    @staticmethod
    def render_text(structured_data: dict[str, list[str] | str]) -> str:
        summary = str(structured_data.get("summary", "")).strip()
        sections = [("Summary", [summary] if summary else [])]
        for key, title in (
            ("key_points", "Key Points"),
            ("decisions", "Decisions"),
            ("action_items", "Action Items"),
            ("risks", "Risks"),
        ):
            values = structured_data.get(key, [])
            if isinstance(values, list):
                items = [str(value).strip() for value in values if str(value).strip()]
            else:
                items = []
            sections.append((title, items))

        blocks: list[str] = []
        for title, items in sections:
            if not items:
                continue
            lines = [title]
            if title == "Summary":
                lines.extend(items)
            else:
                lines.extend(f"- {item}" for item in items)
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.chat.completions.create(**payload)
            return response.model_dump(mode="json")
        except APITimeoutError as exc:
            raise OpenAICompatibleSummaryError("Summary backend request timed out.") from exc
        except APIConnectionError as exc:
            message = str(getattr(exc, "message", "") or exc)
            base_url = str(self.settings.summary_base_url or "")
            cause = str(exc.__cause__) if exc.__cause__ is not None else ""
            details = f"Summary backend connection failed for {base_url}."
            if message and message != "Connection error.":
                details = f"{details} {message}"
            if cause:
                details = f"{details} Cause: {cause}"
            raise OpenAICompatibleSummaryError(details) from exc
        except APIStatusError as exc:
            body = getattr(exc, "body", None)
            if body is None:
                detail = str(exc)
            elif isinstance(body, str):
                detail = body
            else:
                detail = json.dumps(body, ensure_ascii=False)
            raise OpenAICompatibleSummaryError(f"Summary backend HTTP {exc.status_code}: {detail}") from exc
        except json.JSONDecodeError as exc:
            raise OpenAICompatibleSummaryError("Summary backend returned invalid JSON.") from exc

    @staticmethod
    def _extract_content(response_payload: dict[str, Any]) -> str:
        try:
            message_content = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenAICompatibleSummaryError("Summary backend response did not include message content.") from exc

        if isinstance(message_content, str):
            return message_content
        if isinstance(message_content, list):
            parts: list[str] = []
            for item in message_content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            joined = "\n".join(part for part in parts if part.strip())
            if joined:
                return joined
        raise OpenAICompatibleSummaryError("Summary backend returned unsupported message content.")

    @staticmethod
    def _parse_json_content(content: str) -> dict[str, list[str] | str]:
        raw_text = content.strip()
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise OpenAICompatibleSummaryError("Summary backend returned non-JSON content.") from exc

        if not isinstance(parsed, dict):
            raise OpenAICompatibleSummaryError("Summary backend returned a non-object JSON payload.")

        summary = str(parsed.get("summary", "")).strip()
        if not summary:
            raise OpenAICompatibleSummaryError("Summary backend JSON payload did not include a summary.")

        structured_data: dict[str, list[str] | str] = {"summary": summary}
        for key in ("key_points", "decisions", "action_items", "risks"):
            values = parsed.get(key, [])
            if not isinstance(values, list):
                raise OpenAICompatibleSummaryError(f"Summary backend field '{key}' must be a list.")
            structured_data[key] = [str(value).strip() for value in values if str(value).strip()]
        return structured_data

    def _system_prompt(self, summary_language: str) -> str:
        if summary_language == "match-transcript":
            language_instruction = "Match the transcript's primary language."
        else:
            language_instruction = f"Use language '{summary_language}'."
        return (
            "You generate structured meeting summaries. "
            f"Respond only with valid JSON. {language_instruction} "
            "Return an object with keys: summary, key_points, decisions, action_items, risks. "
            "The summary must be a concise paragraph. All list values must be arrays of short strings. "
            "Use empty arrays when a section has no content."
        )

    @staticmethod
    def _user_prompt(text: str) -> str:
        return (
            "Summarize the following meeting transcript or speaker-attributed transcript. "
            "Extract only what is supported by the text.\n\n"
            f"Transcript:\n{text}"
        )