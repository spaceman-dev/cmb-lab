"""Browsable question bank for the assistant.

Every question here is answerable by stage-1 retrieval alone, with no API key. It gives the
assistant a useful shape even without a language model: instead of a blank box the student
gets a curated map of what can be asked, organised the way the physics is organised.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Topic:
    id: str
    label: str
    blurb: str
    icon: str
    questions: list[str]

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "blurb": self.blurb,
            "icon": self.icon,
            "questions": self.questions,
        }


TOPICS: list[Topic] = [
    Topic(
        id="start-here",
        label="Start here",
        blurb="What this project is and what it found.",
        icon="◎",
        questions=[
            "What did our pipeline measure?",
            "What is the first acoustic peak?",
            "How well does our result agree with published data?",
            "What is the CMB?",
        ],
    ),
    Topic(
        id="physics",
        label="The physics",
        blurb="Why the CMB looks the way it does.",
        icon="✦",
        questions=[
            "Why is the first peak at ℓ = 220?",
            "What is a multipole?",
            "What is the angular power spectrum?",
            "What is the sound horizon?",
            "What is an acoustic peak?",
            "What is Silk damping?",
            "What is the Sachs-Wolfe plateau?",
        ],
    ),
    Topic(
        id="method",
        label="How we measured it",
        blurb="The analysis choices, and why each one matters.",
        icon="⚙",
        questions=[
            "What is a cross-spectrum and why did we use one?",
            "What is a beam transfer function?",
            "Why do we need a mask?",
            "Explain cosmic variance",
            "What are unresolved point sources?",
            "What is HEALPix?",
        ],
    ),
    Topic(
        id="cosmology",
        label="Cosmological parameters",
        blurb="Turning a curve into numbers about the universe.",
        icon="∑",
        questions=[
            "What is ΛCDM?",
            "What is the Hubble constant?",
            "What is the Hubble tension?",
            "What is the baryon density?",
        ],
    ),
    Topic(
        id="anomalies",
        label="The anomalies",
        blurb="Four things about the CMB nobody can fully explain.",
        icon="⚠",
        questions=[
            "What is the Axis of Evil?",
            "What is the CMB Cold Spot?",
            "What is the look-elsewhere effect?",
        ],
    ),
    Topic(
        id="using",
        label="Using this site",
        blurb="How to drive the tools.",
        icon="▸",
        questions=[
            "How do I run a power spectrum?",
            "How do I run an MCMC inference?",
            "How do I test the anomalies?",
            "How do I explore the sky maps?",
            "How do I download the data?",
        ],
    ),
]


def all_topics() -> list[dict[str, Any]]:
    return [topic.public() for topic in TOPICS]


def question_count() -> int:
    return sum(len(topic.questions) for topic in TOPICS)
