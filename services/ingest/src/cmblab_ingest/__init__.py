"""Ingest service: acquisition and cleaning of CMB archive products."""

from .pipeline import IngestResult, ingest_product, load_mask
from .registry import DATASETS, DatasetSpec, ProductSpec, get_dataset, get_product

__all__ = [
    "DATASETS",
    "DatasetSpec",
    "IngestResult",
    "ProductSpec",
    "get_dataset",
    "get_product",
    "ingest_product",
    "load_mask",
]
