"""Domain models shared across services.

These are the wire contracts. If a field is not here, it does not cross a service boundary.
"""

from __future__ import annotations

from .anomaly import AnomalyResult, AnomalyStatistic, SimulationBatch
from .catalog import (
    Dataset,
    MapArtifact,
    MapStats,
    Product,
    ProductKind,
    ProvenanceEdge,
)
from .cosmology import CosmoParams, InferenceRun, PosteriorSummary, TheorySpectrum
from .jobs import Job, JobProgress, JobState
from .spectrum import Bandpower, SpectrumComparison, SpectrumMethod, SpectrumResult

__all__ = [
    "AnomalyResult",
    "AnomalyStatistic",
    "Bandpower",
    "CosmoParams",
    "Dataset",
    "InferenceRun",
    "Job",
    "JobProgress",
    "JobState",
    "MapArtifact",
    "MapStats",
    "PosteriorSummary",
    "Product",
    "ProductKind",
    "ProvenanceEdge",
    "SimulationBatch",
    "SpectrumComparison",
    "SpectrumMethod",
    "SpectrumResult",
    "TheorySpectrum",
]
