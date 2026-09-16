"""Catalog domain: datasets, downloadable products, and cleaned map artifacts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductKind(StrEnum):
    MAP = "map"
    MASK = "mask"
    BEAM = "beam"
    SPECTRUM = "spectrum"
    LIKELIHOOD = "likelihood"


class Archive(StrEnum):
    LAMBDA = "LAMBDA"
    PLA = "PLA"
    IRSA = "IRSA"


class Dataset(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    slug: str = Field(description="Stable identifier, e.g. 'wmap9' or 'planck-pr3'")
    name: str
    mission: str
    release: str
    archive: Archive
    reference: str | None = None
    description: str | None = None
    created_at: datetime | None = None


class Product(BaseModel):
    """A single downloadable file in an external archive."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    dataset_id: UUID | None = None
    slug: str
    kind: ProductKind
    url: str
    filename: str

    frequency_ghz: float | None = None
    nside: int | None = None
    component_method: str | None = None
    field_names: list[str] = Field(default_factory=list)
    unit: str | None = None
    coord_system: str = "G"

    size_bytes: int | None = None
    checksum: str | None = None
    checksum_algo: str = "md5"

    storage_uri: str | None = None
    downloaded_at: datetime | None = None
    notes: str | None = None

    @property
    def is_downloaded(self) -> bool:
        return self.storage_uri is not None


class MapStats(BaseModel):
    """Summary statistics computed during cleaning. Drives validation gate G2."""

    monopole_uk: float
    dipole_amp_uk: float
    dipole_lon_deg: float
    dipole_lat_deg: float
    mean_uk: float
    std_uk: float
    min_uk: float
    max_uk: float
    masked_fraction: float
    n_valid_pixels: int


class MapArtifact(BaseModel):
    """A cleaned, analysis-ready HEALPix map."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    source_product_id: UUID
    label: str
    nside: int
    npix: int
    unit: str = "uK"
    coord_system: str = "G"
    ops_applied: list[dict] = Field(default_factory=list)
    stats: MapStats | None = None
    storage_uri: str
    preview_uri: str | None = None
    created_at: datetime | None = None


class ProvenanceEdge(BaseModel):
    child_kind: str
    child_id: UUID
    parent_kind: str
    parent_id: UUID
    relation: str
