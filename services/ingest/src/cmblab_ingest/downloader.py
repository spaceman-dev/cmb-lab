"""Resumable, verified downloads from the CMB archives.

Archive files run to hundreds of megabytes and the ESA PLA rate-limits aggressively, so a
naive ``requests.get`` is not good enough. This module provides:

  * HTTP range resume, so an interrupted 600 MB Planck download continues where it stopped
  * atomic commit via a ``.part`` file, so a partial download is never mistaken for complete
  * SHA-256 recorded on completion, giving us a local integrity check for gate G1
  * retry with exponential backoff on 401/429/5xx, which is how PLA signals rate limiting
"""

from __future__ import annotations

import hashlib
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import httpx
from cmblab_core.net import trust_store_context

ProgressCallback = Callable[[int, int | None], None]

#: PLA returns 401 for rate limiting rather than 429, so it must be treated as retryable.
_RETRYABLE_STATUS = frozenset({401, 408, 429, 500, 502, 503, 504})
_CHUNK_BYTES = 1 << 20  # 1 MiB


@lru_cache(maxsize=1)
def _ssl_context() -> ssl.SSLContext | bool:
    """Verify against the operating system trust store rather than certifi's bundle.

    ESA's pla.esac.esa.int presents a chain that certifi does not carry, so the default
    httpx configuration fails with CERTIFICATE_VERIFY_FAILED while curl succeeds. Using the
    OS trust store matches curl's behaviour and keeps verification fully enabled.
    """
    return trust_store_context() or True


@dataclass(slots=True)
class DownloadResult:
    path: Path
    size_bytes: int
    sha256: str
    resumed: bool
    elapsed_s: float
    from_cache: bool = False

    @property
    def mb(self) -> float:
        return self.size_bytes / (1 << 20)


class DownloadError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _remote_size(client: httpx.Client, url: str) -> int | None:
    try:
        response = client.head(url, follow_redirects=True, timeout=30.0)
        if response.status_code < 400 and (length := response.headers.get("content-length")):
            return int(length)
    except httpx.HTTPError:
        pass
    return None


def _client(timeout: float) -> httpx.Client:
    return httpx.Client(follow_redirects=True, timeout=timeout, verify=_ssl_context())


def download(
    url: str,
    destination: str | Path,
    *,
    expected_sha256: str | None = None,
    resume: bool = True,
    max_retries: int = 5,
    progress: ProgressCallback | None = None,
    timeout: float = 120.0,
) -> DownloadResult:
    """Fetch ``url`` to ``destination``, resuming and retrying as needed.

    If the destination already exists and matches ``expected_sha256`` (or no checksum was
    requested), the download is skipped entirely.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_suffix(destination.suffix + ".part")
    started = time.monotonic()

    if destination.exists():
        digest = _sha256(destination)
        if expected_sha256 is None or digest == expected_sha256:
            return DownloadResult(
                path=destination,
                size_bytes=destination.stat().st_size,
                sha256=digest,
                resumed=False,
                elapsed_s=0.0,
                from_cache=True,
            )
        destination.unlink()  # checksum mismatch: the cached copy is corrupt

    last_error: Exception | None = None

    for attempt in range(max_retries):
        if attempt:
            time.sleep(min(2.0**attempt, 30.0))

        offset = part.stat().st_size if (resume and part.exists()) else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}

        try:
            with _client(timeout) as client:
                total = _remote_size(client, url)

                with client.stream("GET", url, headers=headers) as response:
                    if response.status_code in _RETRYABLE_STATUS:
                        last_error = DownloadError(
                            f"HTTP {response.status_code} from {url} "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        continue
                    response.raise_for_status()

                    # Server ignored our Range header; restart from scratch.
                    if offset and response.status_code != 206:
                        offset = 0
                        part.unlink(missing_ok=True)

                    mode = "ab" if offset else "wb"
                    written = offset
                    with part.open(mode) as handle:
                        for chunk in response.iter_bytes(_CHUNK_BYTES):
                            handle.write(chunk)
                            written += len(chunk)
                            if progress:
                                progress(written, total)

            part.replace(destination)
            digest = _sha256(destination)

            if expected_sha256 and digest != expected_sha256:
                destination.unlink()
                raise DownloadError(
                    f"Checksum mismatch for {url}\n"
                    f"  expected {expected_sha256}\n  got      {digest}"
                )

            return DownloadResult(
                path=destination,
                size_bytes=destination.stat().st_size,
                sha256=digest,
                resumed=offset > 0,
                elapsed_s=time.monotonic() - started,
            )

        except httpx.HTTPError as exc:
            last_error = exc

    raise DownloadError(f"Failed to download {url} after {max_retries} attempts") from last_error
