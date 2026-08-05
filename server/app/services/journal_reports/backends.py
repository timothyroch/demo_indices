from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def _gemini_max_output_tokens() -> int:
    raw = os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "65536")
    try:
        return max(4096, int(raw))
    except ValueError:
        return 65536


def _journal_report_model_fallback_chain() -> list[str]:
    primary = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()
    fallbacks = ("gemini-2.5-flash", "gemini-2.5-flash-lite")
    seen: set[str] = set()
    out: list[str] = []
    for m in (primary, *fallbacks):
        m = m.strip()
        if not m or m in seen:
            continue
        seen.add(m)
        out.append(m)
    return out


_STRICT_JSON_RETRY_SUFFIX = (
    "\n\nLa réponse JSON précédente était incomplète ou invalide. "
    "Produis un JSON complet et valide conforme au schéma ; raccourcis le texte "
    "des champs si nécessaire pour que la sortie tienne entièrement."
)


def _parse_model_output(text: str, model_cls: type[T]) -> T:
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return model_cls.model_validate_json(t)


class JournalReportBackend(ABC):
    @abstractmethod
    def generate_structured(
        self,
        *,
        prompt: str,
        output_model: type[T],
    ) -> T: ...


class MockJournalReportBackend(JournalReportBackend):
    def generate_structured(
        self,
        *,
        prompt: str,
        output_model: type[T],
    ) -> T:
        return output_model(
            title="Rapport (mock)",
            summary=(
                "Mock donc aucun appel LLM et aucune analyse. "
                "Passez GEMINI_API_KEY pour une vraie synthèse"
            ),
            period_description="Mock : période définie précédemment",
            high_risk_events=["Aucune analyse LLM"],
            user_activity_notes=[
                "Entrées de la journalisation présentes dans le prompt envoyé au LLM"
            ],
            recommendations=["Pas de recommandations (mode mock)"],
            usage_overview_bullets=[
                "Mode mock : statistiques d'usage non calculées",
            ],
            detailed_events=[],
            optional_model_data_notes=[],
        )


class GeminiOutlinesBackend(JournalReportBackend):
    def __init__(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY requis pour JOURNAL_REPORT_BACKEND=gemini")

        self._client = genai.Client(api_key=api_key)

    def _generate_structured_with_model(
        self,
        model_name: str,
        *,
        prompt: str,
        output_model: type[T],
    ) -> T:
        schema = output_model.model_json_schema()
        cfg = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=_gemini_max_output_tokens(),
        )
        contents: str = prompt
        for attempt in range(2):
            response = self._client.models.generate_content(
                model=model_name,
                contents=contents,
                config=cfg,
            )
            if not response.text:
                raise ValueError("Réponse vide depuis Gemini.")
            try:
                return _parse_model_output(response.text, output_model)
            except ValidationError as e:
                err = str(e)
                if attempt == 0 and ("json_invalid" in err or "EOF" in err):
                    contents = prompt + _STRICT_JSON_RETRY_SUFFIX
                    continue
                if "json_invalid" in err or "EOF" in err:
                    raise ValueError(
                        "Réponse JSON tronquée ou invalide depuis Gemini "
                        "(sortie trop longue). Augmentez GEMINI_MAX_OUTPUT_TOKENS ou "
                        "réduisez max_entries / la période."
                    ) from e
                raise
        raise RuntimeError("journal report: unexpected Gemini loop exit")

    def generate_structured(
        self,
        *,
        prompt: str,
        output_model: type[T],
    ) -> T:
        errors: list[tuple[str, BaseException]] = []
        for model_name in _journal_report_model_fallback_chain():
            try:
                return self._generate_structured_with_model(
                    model_name,
                    prompt=prompt,
                    output_model=output_model,
                )
            except Exception as e:
                errors.append((model_name, e))
                continue
        msg = (
            "Journal report: échec sur tous les modèles Gemini essayés : "
            + "; ".join(
                f"{name} ({type(exc).__name__}: {exc})" for name, exc in errors
            )
        )
        raise RuntimeError(msg) from errors[-1][1]
