"""Process-wide TLS trust configuration.

Several libraries in this stack open their own HTTPS connections with their own clients:
httpx in the downloader, and urllib inside astropy when healpy lazily fetches pixel window
functions. Configuring each one individually does not scale and misses the ones we do not
control.

``certifi``'s CA bundle does not contain every root these archives chain to — ESA's
pla.esac.esa.int is one confirmed example. The operating system trust store does, which is
why curl succeeds where Python fails. Injecting ``truststore`` into the stdlib ssl module
makes *every* client in the process use the OS trust store, with verification fully on.
"""

from __future__ import annotations

import ssl

_injected = False


def enable_os_trust_store() -> bool:
    """Route all TLS verification through the OS trust store. Idempotent.

    Returns True if injection is active, False if ``truststore`` is unavailable and the
    default certifi behaviour remains in force.
    """
    global _injected
    if _injected:
        return True

    try:
        import truststore
    except ImportError:
        return False

    truststore.inject_into_ssl()
    _injected = True
    return True


def trust_store_context() -> ssl.SSLContext | None:
    """An explicit context for clients that accept one, or None if unavailable."""
    try:
        import truststore
    except ImportError:
        return None
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
