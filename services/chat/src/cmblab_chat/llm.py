"""Stage-2 assistant: a language model grounded in this project's own data.

The design rule is that the model is never the source of a number. Retrieval runs first and
produces facts — glossary entries, lesson excerpts, live pipeline measurements — and those
facts are handed to the model as context with an explicit instruction not to invent
anything outside them. The model's job is to explain and connect, not to recall.

Set ``GEMINI_API_KEY`` in .env to enable. Without it, the service stays in stage 1 and says
so rather than degrading silently.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx
from cmblab_core.net import trust_store_context
from cmblab_tutor.glossary import search_glossary
from cmblab_tutor.live import resolve

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_LIST_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

# Google retires specific model versions on a rolling basis, so a pinned name like
# "gemini-2.0-flash" eventually starts returning 404. The "-latest" aliases are not
# versioned and keep tracking whatever the current generation is, so they are the safe
# default. If a user pins an exact version in .env and it later retires, _discover_model()
# recovers automatically rather than leaving the assistant permanently broken.
DEFAULT_MODEL = "gemini-flash-latest"

# Ordered preference used when we have to pick a replacement ourselves. Earlier is better.
_MODEL_PREFERENCE = ("flash-latest", "flash", "pro-latest", "pro")

# Model names we never want auto-selected: they are specialised, not general chat models.
_MODEL_EXCLUDE = ("image", "tts", "audio", "live", "embedding", "vision", "thinking")

SYSTEM_PROMPT = """You are the resident physicist for cmb-lab, a project that independently
reproduces the cosmic microwave background power spectrum from raw NASA WMAP and ESA Planck
archive data.

Your audience is a graduate-level physics student. They know electromagnetism, statistical
mechanics, and some general relativity. They have not done a CMB analysis before.

Rules you must follow:
1. NEVER invent a numerical result. Only quote numbers that appear in the CONTEXT below. If
   a number is not there, say it has not been measured yet and name the tab that would
   measure it.
2. Derive rather than assert. Build the physical picture first, then write the equation,
   then say why the equation looks the way it does.
3. Use LaTeX for mathematics: $inline$ and $$display$$.
4. Be direct. No filler, no "great question", no restating the question back.
5. If the CONTEXT contradicts your training, the CONTEXT wins — it is measured from real data.
6. Be honest about uncertainty and about the limitations of this pipeline when relevant.

Keep answers under roughly 300 words unless a derivation genuinely needs more."""


@dataclass(slots=True)
class LLMResult:
    text: str
    model: str
    provider: str
    grounded_on: list[str]
    usage: dict[str, Any] | None = None


class LLMUnavailable(RuntimeError):
    pass


def _post(model: str, key: str, payload: dict[str, Any], timeout: float) -> httpx.Response:
    url = GEMINI_ENDPOINT.format(model=model)
    headers = _auth_headers(key)
    try:
        with httpx.Client(timeout=timeout, verify=trust_store_context() or True) as client:
            response = client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise LLMUnavailable(f"Could not reach Gemini: {exc}") from exc

    # Older models reject thinkingConfig outright. Drop it and retry rather than failing.
    if response.status_code == 400 and "thinkingConfig" in payload.get("generationConfig", {}):
        stripped = {**payload, "generationConfig": {**payload["generationConfig"]}}
        stripped["generationConfig"].pop("thinkingConfig", None)
        try:
            with httpx.Client(timeout=timeout, verify=trust_store_context() or True) as client:
                return client.post(url, headers=headers, json=stripped)
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"Could not reach Gemini: {exc}") from exc

    return response


def gemini_api_key() -> str:
    """Read the key from .env (via settings) or the process environment.

    get_settings() is cached, so a key added to .env after start-up needs a service
    restart: `./scripts/dev.sh restart`.
    """
    from cmblab_core.config import get_settings

    return (get_settings().gemini_api_key or os.environ.get("GEMINI_API_KEY", "")).strip()


def gemini_model() -> str:
    from cmblab_core.config import get_settings

    return _RESOLVED_MODEL or get_settings().gemini_model or DEFAULT_MODEL


# Set once we have had to discover a working model, so the lookup happens at most once.
_RESOLVED_MODEL: str | None = None


def _auth_headers(key: str) -> dict[str, str]:
    """Gemini accepts the key as `?key=` or as this header. Prefer the header.

    A key in the query string ends up in access logs, proxy logs, and anything that
    records URLs. A header does not.
    """
    return {"X-goog-api-key": key, "Content-Type": "application/json"}


def list_gemini_models(*, timeout: float = 20.0) -> list[str]:
    """Names of models this key can actually call for text generation."""
    key = gemini_api_key()
    if not key:
        return []
    try:
        with httpx.Client(timeout=timeout, verify=trust_store_context() or True) as client:
            response = client.get(
                GEMINI_LIST_ENDPOINT,
                params={"pageSize": 200},
                headers=_auth_headers(key),
            )
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    names = []
    for entry in response.json().get("models", []):
        if "generateContent" not in entry.get("supportedGenerationMethods", []):
            continue
        name = str(entry.get("name", "")).removeprefix("models/")
        if name and not any(bad in name for bad in _MODEL_EXCLUDE):
            names.append(name)
    return names


def _discover_model() -> str | None:
    """Pick the best currently-available model. Used to recover from a retired name."""
    ranked = _ranked_models()
    return ranked[0] if ranked else None


def _ranked_models() -> list[str]:
    """Available models, best first. Shorter names win: they are the stable aliases."""
    available = list_gemini_models()
    ranked: list[str] = []
    for want in _MODEL_PREFERENCE:
        for name in sorted((n for n in available if want in n), key=len):
            if name not in ranked:
                ranked.append(name)
    return ranked


@lru_cache(maxsize=1)
def _cached_ranked_models() -> tuple[str, ...]:
    return tuple(_ranked_models())


def _fallback_models(*, exclude: str, limit: int = 3) -> list[str]:
    """A short list of alternates to try when `exclude` fails for a model-side reason."""
    return [name for name in _cached_ranked_models() if name != exclude][:limit]


def llm_available() -> bool:
    return bool(gemini_api_key())


def build_context(question: str, *, max_terms: int = 4) -> tuple[str, list[str]]:
    """Assemble grounding facts for the model from retrieval and live measurements."""
    blocks: list[str] = []
    sources: list[str] = []

    for hit in search_glossary(question, limit=max_terms):
        latex = f"\n  Equation: {hit['latex']}" if hit.get("latex") else ""
        blocks.append(f"[GLOSSARY] {hit['term']}: {hit['long']}{latex}")
        sources.append(f"glossary:{hit['key']}")

    # Live pipeline values are the most valuable grounding: they are what makes this
    # assistant able to talk about *this* analysis rather than CMB physics in general.
    measurements = resolve(
        [
            "first_peak_ell",
            "first_peak_dl",
            "chi2_per_dof",
            "f_sky",
            "n_bandpowers",
            "map_rms",
            "beam_labels",
        ]
    )
    measured = [
        f"  - {v['label']}: {v['display']} ({v.get('source', '')})"
        for v in measurements.values()
        if v.get("value") is not None
    ]
    if measured:
        blocks.append("[LIVE MEASUREMENTS FROM THIS PIPELINE]\n" + "\n".join(measured))
        sources.append("pipeline:live")

    blocks.append(
        "[PIPELINE FACTS] This project cross-correlates WMAP V1 and V2 detector maps so "
        "their independent noise cancels, deconvolves WMAP's measured beam transfer "
        "functions, applies the KQ75 Galactic mask, and subtracts an unresolved point "
        "source component. Validation gates: G2 dipole recovery, G3 first acoustic peak, "
        "G4 agreement with published spectra, G5 LCDM parameter recovery via MCMC with "
        "CAMB, G6 Monte Carlo calibration of the anomaly p-values."
    )
    sources.append("pipeline:architecture")

    return "\n\n".join(blocks), sources


def ask_gemini(
    question: str,
    *,
    history: list[dict[str, str]] | None = None,
    model: str | None = None,
    timeout: float = 90.0,
) -> LLMResult:
    """Send a grounded prompt to Gemini and return the reply."""
    key = gemini_api_key()
    if not key:
        raise LLMUnavailable(
            "GEMINI_API_KEY is not set. The assistant is running in stage 1 "
            "(retrieval only). Add a key to .env to enable stage 2."
        )

    model = model or gemini_model()
    context, sources = build_context(question)

    conversation = ""
    for turn in (history or [])[-6:]:
        role = "Student" if turn.get("role") == "user" else "You"
        conversation += f"{role}: {turn.get('content', '')}\n"

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"=== CONTEXT (authoritative, measured from real data) ===\n{context}\n\n"
        f"=== CONVERSATION SO FAR ===\n{conversation or '(new conversation)'}\n\n"
        f"=== STUDENT'S QUESTION ===\n{question}"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "topP": 0.9,
            # Gemini 3.x spends "thinking" tokens out of this same budget, and a long
            # grounding context makes it think hard. A 1200-token cap left almost nothing
            # for the visible answer and truncated it mid-sentence, so the budget is
            # generous and the reasoning effort is explicitly held down.
            "maxOutputTokens": 4096,
            "thinkingConfig": {"thinkingLevel": "low"},
        },
    }

    response = _post(model, key, payload, timeout)

    # Two recoverable failures deserve a second chance on a different model:
    #   404 - the pinned name was retired by Google
    #   503 - that particular model is momentarily overloaded
    # Both are about the *model*, not the request, so trying a sibling usually works.
    if response.status_code in (404, 503):
        global _RESOLVED_MODEL
        for candidate in _fallback_models(exclude=model):
            alt = _post(candidate, key, payload, timeout)
            if alt.status_code < 400:
                _RESOLVED_MODEL = candidate
                model, response = candidate, alt
                break

    if response.status_code == 429:
        raise LLMUnavailable("Gemini rate limit reached. Try again shortly.")
    if response.status_code == 503:
        raise LLMUnavailable("Gemini is overloaded right now. Try again in a moment.")
    if response.status_code >= 400:
        detail = response.text[:200]
        raise LLMUnavailable(f"Gemini returned HTTP {response.status_code}: {detail}")

    body = response.json()
    candidates = body.get("candidates") or []
    if not candidates:
        reason = body.get("promptFeedback", {}).get("blockReason", "no candidates returned")
        raise LLMUnavailable(f"Gemini produced no answer ({reason})")

    candidate = candidates[0]
    # "thought" parts are the model's private reasoning; only real output should be shown.
    parts = candidate.get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    if not text:
        raise LLMUnavailable("Gemini returned an empty answer")

    # A hard token cut-off leaves a dangling half-sentence. A curated answer beats that.
    if candidate.get("finishReason") == "MAX_TOKENS" and len(text) < 400:
        raise LLMUnavailable("Gemini's answer was cut off before it finished")

    return LLMResult(
        text=text,
        model=model,
        provider="gemini",
        grounded_on=sources,
        usage=body.get("usageMetadata"),
    )
