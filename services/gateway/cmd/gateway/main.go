// Command gateway is the public HTTP entry point for cmb-lab.
//
// It routes /api/v1/* to the Python compute services, caches their responses, rate-limits
// per client, and presents one coherent API to the browser.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/cmb-lab/gateway/internal/cache"
	"github.com/cmb-lab/gateway/internal/config"
	"github.com/cmb-lab/gateway/internal/middleware"
	"github.com/cmb-lab/gateway/internal/proxy"
	"github.com/cmb-lab/gateway/internal/static"
)

const apiPrefix = "/api/v1"

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	cfg := config.Load()

	store := cache.NewMemory(cfg.CacheTTL, 512)
	fwd := proxy.New(cfg.UpstreamTimeout, store, logger)

	catalog := proxy.Service{Name: "catalog", BaseURL: cfg.CatalogURL}
	spectrum := proxy.Service{Name: "spectrum", BaseURL: cfg.SpectrumURL}
	cosmology := proxy.Service{Name: "cosmology", BaseURL: cfg.CosmologyURL}
	anomaly := proxy.Service{Name: "anomaly", BaseURL: cfg.AnomalyURL}
	skymap := proxy.Service{Name: "skymap", BaseURL: cfg.SkymapURL}
	tutor := proxy.Service{Name: "tutor", BaseURL: cfg.TutorURL}
	chat := proxy.Service{Name: "chat", BaseURL: cfg.ChatURL}
	playground := proxy.Service{Name: "playground", BaseURL: cfg.PlaygroundURL}

	upstreams := []proxy.Service{
		catalog, spectrum, cosmology, anomaly, skymap, tutor, chat, playground,
	}

	mux := http.NewServeMux()

	// --- meta -------------------------------------------------------------------
	health := func(w http.ResponseWriter, r *http.Request) {
		hits, misses, size := store.Stats()

		// Probe upstreams concurrently: eight sequential 2 s timeouts would make a
		// health check take 16 s when services are down.
		results := make([]map[string]any, len(upstreams))
		var wg sync.WaitGroup
		for i, svc := range upstreams {
			wg.Add(1)
			go func(i int, svc proxy.Service) {
				defer wg.Done()
				results[i] = fwd.Probe(svc)
			}(i, svc)
		}
		wg.Wait()

		down := 0
		for _, res := range results {
			if s, _ := res["status"].(string); s != "ok" {
				down++
			}
		}

		// A container healthcheck has to fail when the app is broken. Returning 200 with
		// a body that says "degraded" would keep a dead container in the load balancer.
		status, code := "ok", http.StatusOK
		switch {
		case down == len(results):
			status, code = "down", http.StatusServiceUnavailable
		case down > 0:
			status = "degraded"
		}

		writeJSON(w, code, map[string]any{
			"status":    status,
			"service":   "gateway",
			"upstreams": results,
			"cache":     map[string]int{"hits": hits, "misses": misses, "size": size},
		})
	}

	mux.HandleFunc("GET "+apiPrefix+"/health", health)

	// Container platforms and load balancers probe /health by convention. Registering it
	// explicitly also stops the SPA catch-all below from swallowing it.
	mux.HandleFunc("GET /health", health)

	// Routes are data, not code. The mux registration and the /routes listing are both
	// generated from this one table, so what the gateway publishes cannot drift from what
	// it actually serves.
	var routes []route
	add := func(svc proxy.Service, strip string, specs ...string) {
		for _, spec := range specs {
			method, path, ok := strings.Cut(spec, " ")
			if !ok {
				panic(`route spec must be "METHOD /path", got: ` + spec)
			}
			routes = append(routes, route{method: method, path: path, svc: svc, strip: strip})
		}
	}

	add(catalog, apiPrefix,
		"GET /datasets",
		"GET /datasets/{slug}/products",
		"GET /datasets/{slug}/products/{product}",
		"GET /maps/{dataset}/{product}/stats",
		"GET /maps/{dataset}/{product}/preview.png",
	)

	add(spectrum, apiPrefix,
		"GET /maps",
		"POST /spectra/cross",
		"POST /spectra/auto",
		"GET /spectra/{id}",
		"GET /references",
		"GET /references/{slug}",
		"GET /parameters/planck2018",
	)

	// G5
	add(cosmology, apiPrefix,
		"GET /parameters",
		"POST /theory",
		"POST /inference/jobs",
		"GET /inference/jobs",
		"GET /inference/jobs/{id}",
		"GET /inference/jobs/{id}/corner",
		"POST /scan",
		"POST /model",
		"GET /tension/H0",
	)

	// G6
	add(anomaly, apiPrefix+"/anomaly",
		"GET /anomaly/statistics",
		"POST /anomaly/measure",
		"POST /anomaly/jobs",
		"GET /anomaly/jobs",
		"GET /anomaly/jobs/{id}",
		"POST /anomaly/calibrate",
	)

	add(skymap, apiPrefix+"/skymap",
		"GET /skymap/projections",
		"GET /skymap/render/{dataset}/{product}",
		"GET /skymap/preset/{dataset}/{product}/{preset}",
		"GET /skymap/sphere/{dataset}/{product}",
		"GET /skymap/profile/{dataset}/{product}",
		"GET /skymap/stats/{dataset}/{product}",
	)

	add(tutor, apiPrefix+"/tutor",
		"GET /tutor/curriculum",
		"GET /tutor/lessons/{id}",
		"GET /tutor/lessons/{id}/sections/{sid}",
		"GET /tutor/audio/{id}/{sid}",
		"GET /tutor/audio/clip/{id}",
		"GET /tutor/audio/voices",
		"POST /tutor/audio/speak",
		"GET /tutor/glossary",
		"GET /tutor/glossary/{term}",
	)

	add(chat, apiPrefix+"/chat",
		"GET /chat/capabilities",
		"GET /chat/topics",
		"POST /chat/chat",
		"GET /chat/sessions/{id}",
		"POST /chat/sessions/{id}/reset",
	)

	add(playground, apiPrefix+"/playground",
		"GET /playground/knobs",
		"GET /playground/experiments",
		"GET /playground/experiments/{id}",
		"POST /playground/experiments/{id}/run",
		"POST /playground/spectrum",
		"POST /playground/theory",
		"POST /playground/compare/spectra",
		"POST /playground/compare/theory",
	)

	for _, rt := range routes {
		mux.HandleFunc(rt.method+" "+apiPrefix+rt.path, fwd.Forward(rt.svc, rt.strip))
	}

	mux.HandleFunc("GET "+apiPrefix+"/routes", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]any{"routes": routeTable(routes)})
	})

	// With STATIC_DIR set, the gateway also serves the built frontend, so the whole app
	// runs behind one port. Unset (local development) it stays API-only and Vite serves
	// the app on its own port.
	if spa := static.New(cfg.StaticDir); spa != nil {
		mux.Handle("/", spa)
		logger.Info("serving frontend", "dir", cfg.StaticDir)
	} else {
		mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
			writeJSON(w, http.StatusNotFound, map[string]any{
				"error":  "not_found",
				"detail": "unknown route; see " + apiPrefix + "/routes",
			})
		})
	}

	limiter := middleware.NewRateLimiter(cfg.RateLimit, cfg.RateBurst)
	handler := middleware.Chain(mux,
		middleware.RequestID,
		middleware.Logger(logger),
		middleware.CORS(cfg.AllowedOrigins),
		limiter.Handler,
	)

	server := &http.Server{
		Addr:              ":" + cfg.Port,
		Handler:           handler,
		ReadHeaderTimeout: 10 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	go func() {
		logger.Info("gateway listening",
			"addr", server.Addr,
			"upstreams", len(upstreams),
		)
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Error("server failed", "err", err)
			os.Exit(1)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)
	<-stop

	logger.Info("shutting down")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := server.Shutdown(ctx); err != nil {
		logger.Error("shutdown failed", "err", err)
	}
}

// route is both registered on the mux and reported by /routes.
type route struct {
	method string
	path   string // relative to apiPrefix
	svc    proxy.Service
	strip  string // prefix removed before the request is forwarded upstream
}

func routeTable(routes []route) []map[string]string {
	table := []map[string]string{
		{"method": "GET", "path": apiPrefix + "/health", "upstream": "gateway"},
		{"method": "GET", "path": apiPrefix + "/routes", "upstream": "gateway"},
	}
	for _, rt := range routes {
		table = append(table, map[string]string{
			"method":   rt.method,
			"path":     apiPrefix + rt.path,
			"upstream": rt.svc.Name,
		})
	}
	return table
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
