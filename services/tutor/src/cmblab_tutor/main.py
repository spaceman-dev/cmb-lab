"""HTTP API for the tutor service: lessons, derivations, and audio explainers."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from cmblab_core.service import create_app
from fastapi import Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .audio import (
    DEFAULT_RATE_WPM,
    default_voice,
    estimate_duration_s,
    installed_voices,
    speakable,
    synthesise,
    tts_available,
)
from .content import CURRICULUM_ORDER, LESSONS, get_lesson, get_section
from .glossary import GLOSSARY, search_glossary
from .live import resolve

app = create_app(
    service_name="tutor",
    description="Derivations, explanations, and audio explainers for CMB physics.",
)

AUDIO_HEADERS = {"Cache-Control": "public, max-age=86400"}


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    voice: str | None = None
    rate: int = Field(default=DEFAULT_RATE_WPM, ge=90, le=300)


@app.get("/curriculum", tags=["lessons"])
async def curriculum() -> dict[str, Any]:
    """Ordered lesson list with prerequisites — the learning path."""
    return {
        "order": CURRICULUM_ORDER,
        "total_minutes": sum(LESSONS[i].duration_min for i in CURRICULUM_ORDER),
        "lessons": [LESSONS[i].summary() for i in CURRICULUM_ORDER],
        "audio": {
            "available": tts_available(),
            "voices": installed_voices()[:12],
            "default_voice": default_voice(),
            "fallback": "browser SpeechSynthesis API",
        },
    }


@app.get("/lessons/{lesson_id}", tags=["lessons"])
async def lesson(
    lesson_id: str,
    with_live: bool = Query(default=True, description="Splice in live pipeline values"),
) -> dict[str, Any]:
    """A complete lesson: narrative, equations, derivations, and measured values."""
    item = get_lesson(lesson_id)
    payload = item.public()

    index = CURRICULUM_ORDER.index(lesson_id)
    payload["navigation"] = {
        "previous": CURRICULUM_ORDER[index - 1] if index > 0 else None,
        "next": (CURRICULUM_ORDER[index + 1] if index < len(CURRICULUM_ORDER) - 1 else None),
        "position": index + 1,
        "total": len(CURRICULUM_ORDER),
    }

    for section in payload["sections"]:
        section["audio"] = {
            "available": tts_available(),
            "estimated_seconds": estimate_duration_s(section["narration"]),
            "url": f"/audio/{lesson_id}/{section['id']}.m4a",
        }
        section["live_values"] = resolve(section.get("live", [])) if with_live else {}

    return payload


@app.get("/lessons/{lesson_id}/sections/{section_id}", tags=["lessons"])
async def section(lesson_id: str, section_id: str) -> dict[str, Any]:
    item = get_section(lesson_id, section_id)
    payload = {
        "lesson_id": lesson_id,
        "id": item.id,
        "title": item.title,
        "narrative": item.narrative,
        "narration": item.narration,
        "equations": [asdict(e) for e in item.equations],
        "derivation": [asdict(s) for s in item.derivation],
        "live_values": resolve(item.live),
        "audio": {
            "available": tts_available(),
            "estimated_seconds": estimate_duration_s(item.narration),
            "url": f"/audio/{lesson_id}/{section_id}.m4a",
        },
    }
    return payload


@app.get("/audio/{lesson_id}/{section_id}.m4a", tags=["audio"])
async def section_audio(
    lesson_id: str,
    section_id: str,
    voice: str | None = Query(default=None),
    rate: int = Query(default=DEFAULT_RATE_WPM, ge=90, le=300),
) -> FileResponse:
    """Synthesised narration for one section. Cached after the first request."""
    item = get_section(lesson_id, section_id)
    clip = synthesise(item.narration, voice=voice, rate=rate)
    return FileResponse(
        clip.path,
        media_type="audio/mp4",
        headers=AUDIO_HEADERS,
        filename=f"{lesson_id}-{section_id}.m4a",
    )


@app.post("/audio/speak", tags=["audio"])
async def speak(request: SpeakRequest) -> dict[str, Any]:
    """Synthesise arbitrary text — used by the chat assistant to read answers aloud."""
    clip = synthesise(request.text, voice=request.voice, rate=request.rate)
    return {
        "id": clip.text_hash,
        "voice": clip.voice,
        "rate": clip.rate,
        "cached": clip.cached,
        "size_bytes": clip.size_bytes,
        "url": f"/audio/clip/{clip.text_hash}.m4a",
        "spoken_text": speakable(request.text)[:400],
    }


@app.get("/audio/clip/{clip_id}.m4a", tags=["audio"])
async def clip(clip_id: str) -> FileResponse:
    from pathlib import Path

    from cmblab_core.config import get_settings

    # Reject anything that is not a bare hex digest: this path is user-supplied and must
    # never be able to escape the cache directory.
    if not clip_id.isalnum() or len(clip_id) > 40:
        raise ValueError("Invalid clip id")

    path = Path(get_settings().data_dir) / "audio" / f"{clip_id}.m4a"
    if not path.exists():
        raise FileNotFoundError(f"No cached clip {clip_id}")
    return FileResponse(path, media_type="audio/mp4", headers=AUDIO_HEADERS)


@app.get("/audio/voices", tags=["audio"])
async def voices() -> dict[str, Any]:
    return {
        "available": tts_available(),
        "voices": installed_voices(),
        "default": default_voice(),
        "default_rate_wpm": DEFAULT_RATE_WPM,
    }


@app.get("/glossary", tags=["glossary"])
async def glossary(q: str | None = Query(default=None)) -> dict[str, Any]:
    if q:
        return {"query": q, "terms": search_glossary(q)}
    return {"terms": [entry.public() for entry in GLOSSARY.values()]}


@app.get("/glossary/{term}", tags=["glossary"])
async def glossary_term(term: str) -> dict[str, Any]:
    key = term.lower().replace(" ", "_")
    if key not in GLOSSARY:
        raise KeyError(f"No glossary entry for {term!r}")
    return GLOSSARY[key].public()
