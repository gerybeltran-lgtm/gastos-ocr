"""Small, fail-safe client for the JEV TypeSafe AI decision API."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from typing import Any

import requests


JEV_DECIDE_URL = "https://jevtypesafeai.com/api/v1/decide"
JEV_TIMEOUT = (2, 8)


class JevUnavailable(RuntimeError):
    """The optional JEV decision service cannot be used safely."""


def _validate_questions(questions: Mapping[str, Mapping[str, Any]]) -> None:
    if not questions:
        raise ValueError("JEV requiere al menos una pregunta")
    for name, question in questions.items():
        if question.get("type") not in {"choice", "score", "noul"}:
            raise ValueError(f"Tipo de pregunta JEV inválido: {name}")
        if not str(question.get("instructions", "")).strip():
            raise ValueError(f"instructions es obligatorio para: {name}")
        if question["type"] == "choice" and not question.get("criteria"):
            raise ValueError(f"criteria es obligatorio para choice: {name}")


def decide(*, state: str | Mapping[str, Any], questions: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Ask JEV for a typed decision without logging sensitive input or tokens."""
    api_key = os.environ.get("JEV_API_KEY", "").strip()
    if not api_key:
        raise JevUnavailable("JEV_API_KEY no está configurada")
    _validate_questions(questions)
    payload = {
        "state": state if isinstance(state, str) else json.dumps(state, ensure_ascii=False, separators=(",", ":")),
        "questions": questions,
    }
    try:
        response = requests.post(
            JEV_DECIDE_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=JEV_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise JevUnavailable("JEV no está disponible") from exc
    if not isinstance(result, dict) or not isinstance(result.get("answers"), dict):
        raise JevUnavailable("Respuesta JEV inválida")
    return result


def decide_or_fallback(
    *,
    state: str | Mapping[str, Any],
    questions: Mapping[str, Mapping[str, Any]],
    fallback: Callable[[], dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    """Return a deterministic fallback when JEV is unavailable or rejects a payload."""
    try:
        return decide(state=state, questions=questions), False
    except (JevUnavailable, ValueError):
        return fallback(), True
