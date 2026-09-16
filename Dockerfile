# cmb-lab in a single container.
#
# Everything — eight Python services, the Go gateway, and the built frontend — runs behind
# one port, because container platforms (Hugging Face Spaces, Cloud Run, Fly, Render) only
# expose one. The gateway serves web/dist directly when STATIC_DIR is set.
#
#   docker build -t cmb-lab .
#   docker run -p 7860:7860 cmb-lab
#
# Needs ~6 GB RAM at runtime and ~8 GB during the build (CAMB compiles Fortran).

# ── Stage 1: frontend ───────────────────────────────────────────────────────────────────
FROM node:20-slim AS web
WORKDIR /build
COPY web/package*.json ./web/
RUN npm --prefix web ci --silent
COPY web/ ./web/
RUN npm --prefix web run build

# ── Stage 2: gateway ────────────────────────────────────────────────────────────────────
FROM golang:1.24-bookworm AS gateway
WORKDIR /build
COPY services/gateway/ ./
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /gateway ./cmd/gateway

# ── Stage 3: runtime ────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

# gfortran and the BLAS/cfitsio headers are needed to build CAMB and healpy. They are kept
# in the final image because pip installs the packages in editable mode.
RUN apt-get update && apt-get install -y --no-install-recommends \
      gfortran build-essential pkg-config \
      libcfitsio-dev libopenblas-dev \
      curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Containers on these platforms often run as an arbitrary non-root UID, so everything the
# app writes has to live somewhere world-writable and predictable.
ENV APP_HOME=/app \
    DATA_DIR=/app/data \
    STATIC_DIR=/app/web/dist \
    GATEWAY_PORT=7860 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# One thread per process: eight services each spawning a BLAS thread pool on a 2-core box
# is heavy oversubscription. The process pools inside cosmology/anomaly do the real work.
ENV OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    VECLIB_MAXIMUM_THREADS=1

WORKDIR $APP_HOME

COPY libs/ ./libs/
COPY services/ ./services/
COPY pyproject.toml ./

RUN pip install --upgrade pip wheel \
    && pip install -e libs/cmblab-core \
    && for s in ingest catalog spectrum cosmology anomaly skymap tutor chat playground; do \
         pip install -e "services/$s" || exit 1; \
       done

COPY --from=web /build/web/dist ./web/dist
COPY --from=gateway /gateway /usr/local/bin/gateway
COPY deploy/docker/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

# Bake the archive data into the image so the container starts ready to use. If the build
# environment has no network, this is skipped and start.sh fetches it on first boot.
RUN mkdir -p "$DATA_DIR" \
    && (cmblab-ingest bootstrap || echo "data download skipped; will retry at startup") \
    && chmod -R 777 "$DATA_DIR"

RUN chmod -R 777 "$APP_HOME/data" 2>/dev/null || true

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
  CMD curl -fsS "http://localhost:${GATEWAY_PORT}/health" || exit 1

CMD ["/usr/local/bin/start.sh"]
