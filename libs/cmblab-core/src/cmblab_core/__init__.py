"""Shared building blocks for every cmb-lab service."""

from .net import enable_os_trust_store

__version__ = "0.1.0"

# Archives (ESA PLA) and lazily-downloaded healpy data files chain to roots that certifi
# does not carry. Do this at import so every HTTP client in the process inherits it.
enable_os_trust_store()

__all__ = ["enable_os_trust_store"]
