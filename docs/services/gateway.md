# gateway

**Path:** `services/gateway/` · **Port:** 8080 · **Language:** Go

The single public entry point. The browser talks only to the gateway; the gateway talks to
the eight Python services.

## Why a separate gateway, and why Go

Three reasons it is not just CORS config on each service:

1. **One origin for the browser.** The frontend calls `/api/v1/...` and never needs to know
   which service owns an endpoint, or that there are eight of them.
2. **Caching where it pays.** Sky map PNGs and theory spectra are expensive to produce and
   identical for identical inputs. The gateway caches them so CAMB is not re-run for a
   request it already answered.
3. **A health view of the whole system.** `/health` probes every backend concurrently and
   reports one table — which is what `./scripts/dev.sh status` renders.

Go specifically because this layer is pure I/O concurrency: fan-out health probes, request
forwarding, and a TTL cache. It compiles to a single static binary with no runtime.

## Layout

```
cmd/gateway/main.go          route table, health aggregation
internal/config/             environment-driven configuration
internal/cache/              TTL cache, SHA-256 keys
internal/middleware/         request ID, logging, CORS, rate limiting
internal/proxy/              forwarding to backends
```

## Routes

Everything is mounted under `/api/v1`. The gateway uses Go 1.22+ pattern routing
(`"GET /api/v1/..."`), so the method is part of the pattern.

| Prefix | Backend |
| --- | --- |
| `/api/v1/catalog/*` | catalog :8001 |
| `/api/v1/spectrum/*` | spectrum :8003 |
| `/api/v1/cosmology/*` | cosmology :8004 |
| `/api/v1/anomaly/*` | anomaly :8005 |
| `/api/v1/skymap/*` | skymap :8007 |
| `/api/v1/tutor/*` | tutor :8008 |
| `/api/v1/chat/*` | chat :8009 |
| `/api/v1/playground/*` | playground :8010 |

Plus `GET /health`, which probes all backends in parallel with a `sync.WaitGroup` and
returns each one's status.

> Routes are registered explicitly, not with a catch-all prefix. Adding an endpoint to a
> Python service therefore requires adding a line to `main.go` and rebuilding. That is
> deliberate — the gateway is the list of what is actually public.

## Middleware

| Middleware | Behaviour |
| --- | --- |
| Request ID | Generates one if the client did not send `X-Request-ID`, forwards it downstream, returns it in the response |
| Logger | One structured line per request: method, path, status, duration |
| CORS | Allows the Vite dev origins |
| Rate limit | Per-IP token bucket, protects the expensive compute endpoints |

## Caching

`internal/cache` is a TTL map keyed by a SHA-256 of method, path, query, and body. Applied
to deterministic, expensive responses — rendered PNGs and theory spectra. Job endpoints and
anything with mutable state are never cached.

## Building and running

```bash
make gateway-build     # writes services/gateway/bin/gateway
make gateway           # build and run
```

The build is pinned to a vendored toolchain because Homebrew's Go was unavailable on the
development machine:

```bash
GOTOOLCHAIN=local \
GOPATH=$PWD/.toolchain/gopath \
CGO_ENABLED=0 \
.toolchain/go/bin/go build -o bin/gateway ./cmd/gateway
```

`CGO_ENABLED=0` keeps the binary static.

## Configuration

Backend URLs and the listen port come from the environment, with defaults matching the
local port map. See `internal/config/`.

## Checks

```bash
cd services/gateway && go vet ./...
```
