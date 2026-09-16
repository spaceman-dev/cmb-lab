"""Audio explainers, synthesised locally.

macOS ships a perfectly good speech synthesiser (``say``) and an audio converter
(``afconvert``), so the audio explainers need no cloud service, no API key, and no per-
request cost. Clips are content-addressed and cached on disk, so each one is synthesised
exactly once.

If either binary is missing — Linux, CI — the API reports ``available: false`` and the
frontend falls back to the browser's built-in SpeechSynthesis API.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from cmblab_core.config import get_settings

#: Voices that read technical prose clearly. Checked against the installed set at runtime.
PREFERRED_VOICES = ("Samantha", "Daniel", "Karen", "Moira", "Alex", "Tom")

DEFAULT_RATE_WPM = 165

#: Spoken forms for symbols that appear in the narration text.
_SPOKEN: list[tuple[str, str]] = [
    (r"\bC_?\\?ell\b", "C sub ell"),
    (r"\bD_?\\?ell\b", "D sub ell"),
    (r"\ba_\{?\\?ell\s*m\}?\b", "a ell m"),
    (r"ℓ", "ell"),
    (r"µK|μK", "microkelvin"),
    (r"\bK\b", "kelvin"),
    (r"χ²|chi\^2", "chi squared"),
    (r"σ8|sigma_?8", "sigma eight"),
    (r"Ω_?b", "omega baryon"),
    (r"Ω_?c", "omega cold dark matter"),
    (r"Ω_?m", "omega matter"),
    (r"Ω_?Λ", "omega lambda"),
    (r"Ω_?k", "omega curvature"),
    (r"H₀|H_?0\b", "H naught"),
    (r"n_?s\b", "n sub s"),
    (r"A_?s\b", "A sub s"),
    (r"ΛCDM", "lambda C D M"),
    (r"τ", "tau"),
    (r"θ", "theta"),
    (r"≈|~", " approximately "),
    (r"×", " times "),
    (r"°", " degrees"),
    (r"—|–", ", "),
]


@dataclass(slots=True)
class AudioClip:
    path: Path
    text_hash: str
    voice: str
    rate: int
    size_bytes: int
    cached: bool


def _binary(name: str) -> str | None:
    return shutil.which(name)


@lru_cache(maxsize=1)
def tts_available() -> bool:
    return bool(_binary("say") and _binary("afconvert"))


@lru_cache(maxsize=1)
def installed_voices() -> list[str]:
    """English voices available on this machine, preferred ones first."""
    if not _binary("say"):
        return []

    try:
        output = subprocess.run(
            ["say", "-v", "?"], capture_output=True, text=True, timeout=10, check=False
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return []

    english = [
        line.split()[0]
        for line in output.splitlines()
        if len(line.split()) > 1 and line.split()[1].startswith("en_")
    ]
    preferred = [v for v in PREFERRED_VOICES if v in english]
    return preferred + [v for v in english if v not in preferred]


def default_voice() -> str:
    voices = installed_voices()
    return voices[0] if voices else "Samantha"


def speakable(text: str) -> str:
    """Convert narration prose into something a synthesiser reads naturally.

    Mathematical notation is the problem: a synthesiser confronted with "C_ℓ" will either
    spell it out letter by letter or skip it. Substituting the spoken form first makes the
    audio track match how a lecturer would actually say the symbol out loud.
    """
    cleaned = text.strip()

    # Strip any stray LaTeX that leaked into a narration field.
    cleaned = re.sub(r"\$\$?[^$]*\$\$?", " ", cleaned)
    cleaned = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", cleaned)
    cleaned = re.sub(r"\\[a-zA-Z]+", " ", cleaned)

    for pattern, replacement in _SPOKEN:
        cleaned = re.sub(pattern, replacement, cleaned)

    cleaned = re.sub(r"[*_`#>|]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _cache_dir() -> Path:
    path = Path(get_settings().data_dir) / "audio"
    path.mkdir(parents=True, exist_ok=True)
    return path


def synthesise(
    text: str,
    *,
    voice: str | None = None,
    rate: int = DEFAULT_RATE_WPM,
    force: bool = False,
) -> AudioClip:
    """Render narration to a cached AAC clip and return its path."""
    if not tts_available():
        raise RuntimeError(
            "Local speech synthesis is unavailable (needs macOS `say` and `afconvert`). "
            "The frontend falls back to the browser SpeechSynthesis API."
        )

    voice = voice or default_voice()
    spoken = speakable(text)
    if not spoken:
        raise ValueError("Nothing to synthesise")

    digest = hashlib.sha256(f"{voice}|{rate}|{spoken}".encode()).hexdigest()[:20]
    target = _cache_dir() / f"{digest}.m4a"

    if target.exists() and not force:
        return AudioClip(
            path=target,
            text_hash=digest,
            voice=voice,
            rate=rate,
            size_bytes=target.stat().st_size,
            cached=True,
        )

    raw = target.with_suffix(".aiff")
    try:
        subprocess.run(
            ["say", "-v", voice, "-r", str(rate), "-o", str(raw), spoken],
            check=True,
            capture_output=True,
            timeout=180,
        )
        # AAC in an MP4 container plays natively in every current browser.
        subprocess.run(
            ["afconvert", "-f", "m4af", "-d", "aac", str(raw), str(target)],
            check=True,
            capture_output=True,
            timeout=180,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace") if exc.stderr else str(exc)
        raise RuntimeError(f"Speech synthesis failed: {detail}") from exc
    finally:
        raw.unlink(missing_ok=True)

    return AudioClip(
        path=target,
        text_hash=digest,
        voice=voice,
        rate=rate,
        size_bytes=target.stat().st_size,
        cached=False,
    )


def estimate_duration_s(text: str, rate: int = DEFAULT_RATE_WPM) -> float:
    words = len(speakable(text).split())
    return round(60.0 * words / max(rate, 1), 1)
