// Package proxy forwards gateway requests to the Python compute services.
package proxy

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"github.com/cmb-lab/gateway/internal/cache"
)

// Service is a named upstream.
type Service struct {
	Name    string
	BaseURL string
}

// Proxy forwards requests to upstreams, with caching for idempotent calls.
type Proxy struct {
	client  *http.Client
	store   cache.Store
	logger  *slog.Logger
	cacheOn bool
}

func New(timeout time.Duration, store cache.Store, logger *slog.Logger) *Proxy {
	return &Proxy{
		client:  &http.Client{Timeout: timeout},
		store:   store,
		logger:  logger,
		cacheOn: store != nil,
	}
}

// cacheKey hashes method, target and body so that POSTs with identical parameters —
// which is how spectrum estimation is invoked — reuse the same cached result.
func cacheKey(method, url string, body []byte) string {
	h := sha256.New()
	h.Write([]byte(method))
	h.Write([]byte(url))
	h.Write(body)
	return hex.EncodeToString(h.Sum(nil))[:24]
}

// Forward proxies the request to svc, rewriting the path with stripPrefix removed.
func (p *Proxy) Forward(svc Service, stripPrefix string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		upstreamPath := strings.TrimPrefix(r.URL.Path, stripPrefix)
		if !strings.HasPrefix(upstreamPath, "/") {
			upstreamPath = "/" + upstreamPath
		}
		target := svc.BaseURL + upstreamPath
		if r.URL.RawQuery != "" {
			target += "?" + r.URL.RawQuery
		}

		var body []byte
		if r.Body != nil {
			body, _ = io.ReadAll(io.LimitReader(r.Body, 1<<20))
			_ = r.Body.Close()
		}

		// GET and POST are both safe to cache here: every endpoint behind this gateway is
		// a pure function of its inputs. Nothing mutates server state.
		key := cacheKey(r.Method, target, body)
		if p.cacheOn {
			if entry, ok := p.store.Get(key); ok {
				w.Header().Set("Content-Type", entry.ContentType)
				w.Header().Set("X-Cache", "HIT")
				w.Header().Set("X-Upstream", svc.Name)
				w.WriteHeader(entry.Status)
				_, _ = w.Write(entry.Body)
				return
			}
		}

		req, err := http.NewRequestWithContext(r.Context(), r.Method, target, bytes.NewReader(body))
		if err != nil {
			writeError(w, http.StatusInternalServerError, "bad_upstream_request", err.Error())
			return
		}
		if ct := r.Header.Get("Content-Type"); ct != "" {
			req.Header.Set("Content-Type", ct)
		}
		req.Header.Set("X-Request-ID", r.Header.Get("X-Request-ID"))

		resp, err := p.client.Do(req)
		if err != nil {
			p.logger.Error("upstream unreachable", "service", svc.Name, "target", target, "err", err)
			writeError(w, http.StatusBadGateway, "upstream_unavailable",
				svc.Name+" is not responding. Is it running? Try `make dev-"+svc.Name+"`.")
			return
		}
		defer resp.Body.Close()

		payload, err := io.ReadAll(resp.Body)
		if err != nil {
			writeError(w, http.StatusBadGateway, "upstream_read_failed", err.Error())
			return
		}

		contentType := resp.Header.Get("Content-Type")
		if p.cacheOn && resp.StatusCode == http.StatusOK {
			p.store.Set(key, cache.Entry{
				Status:      resp.StatusCode,
				ContentType: contentType,
				Body:        payload,
			})
		}

		w.Header().Set("Content-Type", contentType)
		w.Header().Set("X-Cache", "MISS")
		w.Header().Set("X-Upstream", svc.Name)
		w.WriteHeader(resp.StatusCode)
		_, _ = w.Write(payload)
	}
}

// Probe reports whether an upstream's health endpoint answers.
func (p *Proxy) Probe(svc Service) map[string]any {
	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(svc.BaseURL + "/health")
	if err != nil {
		return map[string]any{"service": svc.Name, "status": "down", "url": svc.BaseURL}
	}
	defer resp.Body.Close()

	status := "down"
	if resp.StatusCode == http.StatusOK {
		status = "ok"
	}
	return map[string]any{"service": svc.Name, "status": status, "url": svc.BaseURL}
}

func writeError(w http.ResponseWriter, status int, code, detail string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": code, "detail": detail})
}
