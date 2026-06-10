from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from src.app.core.content_paths import (
    FALLBACK_PERSONALITY_FILENAME,
    LINKEDIN_FILENAME,
    STYLE_FILENAME,
    SUMMARY_FILENAME,
    resolve_data_path,
)

from .facts_loader import FactsLoader, InvalidContentError, MissingContentError

LINKEDIN_NOT_AVAILABLE = "LinkedIn profile not available"


@dataclass(frozen=True)
class PromptResources:
    linkedin: str
    summary: str
    facts: dict[str, Any]
    style: str


class ResourceLoader:
    def __init__(
        self,
        data_dir: Path,
        facts_loader: FactsLoader | None = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.facts_loader = facts_loader or FactsLoader(self.data_dir)

    def resolve_path(self, filename: str) -> Path:
        return resolve_data_path(filename, data_dir=self.data_dir)

    def load_summary(self) -> str:
        return self._read_required_text(SUMMARY_FILENAME, label="summary")

    def load_style(self) -> str:
        return self._read_required_text(STYLE_FILENAME, label="style")

    def load_fallback_personality(self) -> str:
        return self._read_required_text(
            FALLBACK_PERSONALITY_FILENAME,
            label="fallback personality",
        )

    def load_linkedin(self) -> str:
        path = self.resolve_path(LINKEDIN_FILENAME)
        if not path.exists():
            return LINKEDIN_NOT_AVAILABLE

        try:
            reader = PdfReader(str(path))
        except OSError as exc:
            raise InvalidContentError(
                f"Unable to read PDF resource file: {path}"
            ) from exc
        except Exception as exc:
            raise InvalidContentError(f"Invalid PDF resource file: {path}") from exc

        linkedin_parts: list[str] = []
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text()
            except Exception as exc:
                raise InvalidContentError(
                    f"Unable to extract text from PDF resource file: {path} (page {page_number})"
                ) from exc
            if text:
                linkedin_parts.append(text)

        return "".join(linkedin_parts)

    def load_prompt_resources(self) -> PromptResources:
        return PromptResources(
            linkedin=self.load_linkedin(),
            summary=self.load_summary(),
            facts=self.facts_loader.load(),
            style=self.load_style(),
        )

    def build_prompt_context(
        self,
        now: datetime | None = None,
    ) -> dict[str, str]:
        resources = self.load_prompt_resources()
        facts = resources.facts
        name = facts["name"]
        rendered_datetime = (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

        return {
            "full_name": facts["full_name"],
            "name": name,
            "profile": str(facts),
            "profile_heading": f"Here is some basic information about {name}:",
            "summary": resources.summary,
            "summary_heading": f"Here are summary notes from {name}:",
            "linkedin": resources.linkedin,
            "linkedin_heading": f"Here is the LinkedIn profile of {name}:",
            "style": resources.style,
            "style_heading": f"Here are some notes from {name} about their communications style:",
            "contact_links": self._contact_block(
                email=facts.get("email"),
                linkedin_url=facts.get("linkedin"),
                github_url=facts.get("github"),
            ),
            "contact_links_heading": f"Here are direct contact/profile links for {name} (share these when asked):",
            "current_datetime": rendered_datetime,
        }

    def _read_required_text(self, filename: str, *, label: str) -> str:
        path = self.resolve_path(filename)
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise MissingContentError(
                f"Required {label} file not found: {path}"
            ) from exc
        except OSError as exc:
            raise InvalidContentError(f"Unable to read {label} file: {path}") from exc

    @staticmethod
    def _contact_block(
        *,
        email: str | None,
        linkedin_url: str | None,
        github_url: str | None,
    ) -> str:
        items: list[str] = []
        if email:
            items.append(f"- Email: {email}")
        if linkedin_url:
            items.append(f"- LinkedIn: {ResourceLoader._as_url(linkedin_url)}")
        if github_url:
            items.append(f"- GitHub: {ResourceLoader._as_url(github_url)}")

        if not items:
            return "No direct contact or profile links are available."
        return "\n".join(items)

    @staticmethod
    def _as_url(value: str | None) -> str | None:
        if not value:
            return None
        if value.startswith(("http://", "https://")):
            return value
        return f"https://{value}"
