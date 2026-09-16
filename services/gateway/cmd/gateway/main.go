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
	"sync"
	"syscall"
	"time"

	"github.com/cmb-lab/gateway/internal/cache"
	"github.com/cmb-lab/gateway/internal/config"
	"github.com/cmb-lab/gateway/internal/middleware"
	"github.com/cmb-lab/gateway/internal/proxy"
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
	mux.HandleFunc("GET "+apiPrefix+"/health", func(w http.ResponseWriter, r *http.Request) {
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

		writeJSON(w, http.StatusOK, map[string]any{
			"status":    "ok",
			"service":   "gateway",
			"upstreams": results,
			"cache":     map[string]int{"hits": hits, "misses": misses, "size": size},
		})
	})

	mux.HandleFunc("GET "+apiPrefix+"/routes", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]any{"routes": routeTable()})
	})

	// --- catalog ----------------------------------------------------------------
	mux.HandleFunc("GET "+apiPrefix+"/datasets", fwd.Forward(catalog, apiPrefix))
	mux.HandleFunc("GET "+apiPrefix+"/datasets/{slug}/products", fwd.Forward(catalog, apiPrefix))
	mux.HandleFunc("GET "+apiPrefix+"/datasets/{slug}/products/{product}", fwd.Forward(catalog, apiPrefix))
	mux.HandleFunc("GET "+apiPrefix+"/maps/{dataset}/{product}/stats", fwd.Forward(catalog, apiPrefix))
	mux.HandleFunc("GET "+apiPrefix+"/maps/{dataset}/{product}/preview.png", fwd.Forward(catalog, apiPrefix))

	// --- spectrum ---------------------------------------------------------------
	mux.HandleFunc("GET "+apiPrefix+"/maps", fwd.Forward(spectrum, apiPrefix))
	mux.HandleFunc("POST "+apiPrefix+"/spectra/cross", fwd.Forward(spectrum, apiPrefix))
	mux.HandleFunc("POST "+apiPrefix+"/spectra/auto", fwd.Forward(spectrum, apiPrefix))
	mux.HandleFunc("GET "+apiPrefix+"/spectra/{id}", fwd.Forward(spectrum, apiPrefix))
	mux.HandleFunc("GET "+apiPrefix+"/references", fwd.Forward(spectrum, apiPrefix))
	mux.HandleFunc("GET "+apiPrefix+"/references/{slug}", fwd.Forward(spectrum, apiPrefix))
	mux.HandleFunc("GET "+apiPrefix+"/parameters/planck2018", fwd.Forward(spectrum, apiPrefix))

	// --- cosmology (G5) ---------------------------------------------------------
	mux.HandleFunc("GET "+apiPrefix+"/parameters", fwd.Forward(cosmology, apiPrefix))
	mux.HandleFunc("POST "+apiPrefix+"/theory", fwd.Forward(cosmology, apiPrefix))
	mux.HandleFunc("POST "+apiPrefix+"/inference/jobs", fwd.Forward(cosmology, apiPrefix))
	mux.HandleFunc("GET "+apiPrefix+"/inference/jobs", fwd.Forward(cosmology, apiPrefix))
	mux.HandleFunc("GET "+apiPrefix+"/inference/jobs/{id}", fwd.Forward(cosmology, apiPrefix))
	mux.HandleFunc("GET "+apiPrefix+"/inference/jobs/{id}/corner", fwd.Forward(cosmology, apiPrefix))
	mux.HandleFunc("POST "+apiPrefix+"/scan", fwd.Forward(cosmology, apiPrefix))
	mux.HandleFunc("POST "+apiPrefix+"/model", fwd.Forward(cosmology, apiPrefix))
	mux.HandleFunc("GET "+apiPrefix+"/tension/H0", fwd.Forward(cosmology, apiPrefix))

	// --- anomaly (G6) -----------------------------------------------------------
	mux.HandleFunc("GET "+apiPrefix+"/anomaly/statistics", fwd.Forward(anomaly, apiPrefix+"/anomaly"))
	mux.HandleFunc("POST "+apiPrefix+"/anomaly/measure", fwd.Forward(anomaly, apiPrefix+"/anomaly"))
	mux.HandleFunc("POST "+apiPrefix+"/anomaly/jobs", fwd.Forward(anomaly, apiPrefix+"/anomaly"))
	mux.HandleFunc("GET "+apiPrefix+"/anomaly/jobs", fwd.Forward(anomaly, apiPrefix+"/anomaly"))
	mux.HandleFunc("GET "+apiPrefix+"/anomaly/jobs/{id}", fwd.Forward(anomaly, apiPrefix+"/anomaly"))
	mux.HandleFunc("POST "+apiPrefix+"/anomaly/calibrate", fwd.Forward(anomaly, apiPrefix+"/anomaly"))

	// --- skymap -----------------------------------------------------------------
	mux.HandleFunc("GET "+apiPrefix+"/skymap/projections", fwd.Forward(skymap, apiPrefix+"/skymap"))
	mux.HandleFunc("GET "+apiPrefix+"/skymap/render/{dataset}/{product}", fwd.Forward(skymap, apiPrefix+"/skymap"))
	mux.HandleFunc("GET "+apiPrefix+"/skymap/preset/{dataset}/{product}/{preset}", fwd.Forward(skymap, apiPrefix+"/skymap"))
	mux.HandleFunc("GET "+apiPrefix+"/skymap/sphere/{dataset}/{product}", fwd.Forward(skymap, apiPrefix+"/skymap"))
	mux.HandleFunc("GET "+apiPrefix+"/skymap/profile/{dataset}/{product}", fwd.Forward(skymap, apiPrefix+"/skymap"))
	mux.HandleFunc("GET "+apiPrefix+"/skymap/stats/{dataset}/{product}", fwd.Forward(skymap, apiPrefix+"/skymap"))

	// --- tutor ------------------------------------------------------------------
	mux.HandleFunc("GET "+apiPrefix+"/tutor/curriculum", fwd.Forward(tutor, apiPrefix+"/tutor"))
	mux.HandleFunc("GET "+apiPrefix+"/tutor/lessons/{id}", fwd.Forward(tutor, apiPrefix+"/tutor"))
	mux.HandleFunc("GET "+apiPrefix+"/tutor/lessons/{id}/sections/{sid}", fwd.Forward(tutor, apiPrefix+"/tutor"))
	mux.HandleFunc("GET "+apiPrefix+"/tutor/audio/{id}/{sid}", fwd.Forward(tutor, apiPrefix+"/tutor"))
	mux.HandleFunc("GET "+apiPrefix+"/tutor/audio/clip/{id}", fwd.Forward(tutor, apiPrefix+"/tutor"))
	mux.HandleFunc("GET "+apiPrefix+"/tutor/audio/voices", fwd.Forward(tutor, apiPrefix+"/tutor"))
	mux.HandleFunc("POST "+apiPrefix+"/tutor/audio/speak", fwd.Forward(tutor, apiPrefix+"/tutor"))
	mux.HandleFunc("GET "+apiPrefix+"/tutor/glossary", fwd.Forward(tutor, apiPrefix+"/tutor"))
	mux.HandleFunc("GET "+apiPrefix+"/tutor/glossary/{term}", fwd.Forward(tutor, apiPrefix+"/tutor"))

	// --- chat -------------------------------------------------------------------
	mux.HandleFunc("GET "+apiPrefix+"/chat/capabilities", fwd.Forward(chat, apiPrefix+"/chat"))
	mux.HandleFunc("GET "+apiPrefix+"/chat/topics", fwd.Forward(chat, apiPrefix+"/chat"))
	mux.HandleFunc("POST "+apiPrefix+"/chat/chat", fwd.Forward(chat, apiPrefix+"/chat"))
	mux.HandleFunc("GET "+apiPrefix+"/chat/sessions/{id}", fwd.Forward(chat, apiPrefix+"/chat"))
	mux.HandleFunc("POST "+apiPrefix+"/chat/sessions/{id}/reset", fwd.Forward(chat, apiPrefix+"/chat"))

	// --- playground -------------------------------------------------------------
	mux.HandleFunc("GET "+apiPrefix+"/playground/knobs", fwd.Forward(playground, apiPrefix+"/playground"))
	mux.HandleFunc("GET "+apiPrefix+"/playground/experiments", fwd.Forward(playground, apiPrefix+"/playground"))
	mux.HandleFunc("GET "+apiPrefix+"/playground/experiments/{id}", fwd.Forward(playground, apiPrefix+"/playground"))
	mux.HandleFunc("POST "+apiPrefix+"/playground/experiments/{id}/run", fwd.Forward(playground, apiPrefix+"/playground"))
	mux.HandleFunc("POST "+apiPrefix+"/playground/spectrum", fwd.Forward(playground, apiPrefix+"/playground"))
	mux.HandleFunc("POST "+apiPrefix+"/playground/theory", fwd.Forward(playground, apiPrefix+"/playground"))
	mux.HandleFunc("POST "+apiPrefix+"/playground/compare/spectra", fwd.Forward(playground, apiPrefix+"/playground"))
	mux.HandleFunc("POST "+apiPrefix+"/playground/compare/theory", fwd.Forward(playground, apiPrefix+"/playground"))

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusNotFound, map[string]any{
			"error":  "not_found",
			"detail": "unknown route; see " + apiPrefix + "/routes",
		})
	})

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

func routeTable() []map[string]string {
	return []map[string]string{
		{"method": "GET", "path": apiPrefix + "/health", "upstream": "gateway"},
		{"method": "GET", "path": apiPrefix + "/datasets", "upstream": "catalog"},
		{"method": "GET", "path": apiPrefix + "/datasets/{slug}/products", "upstream": "catalog"},
		{"method": "GET", "path": apiPrefix + "/maps", "upstream": "spectrum"},
		{"method": "GET", "path": apiPrefix + "/maps/{dataset}/{product}/stats", "upstream": "catalog"},
		{"method": "GET", "path": apiPrefix + "/maps/{dataset}/{product}/preview.png", "upstream": "catalog"},
		{"method": "POST", "path": apiPrefix + "/spectra/cross", "upstream": "spectrum"},
		{"method": "POST", "path": apiPrefix + "/spectra/auto", "upstream": "spectrum"},
		{"method": "GET", "path": apiPrefix + "/references", "upstream": "spectrum"},
		{"method": "GET", "path": apiPrefix + "/references/{slug}", "upstream": "spectrum"},
		{"method": "GET", "path": apiPrefix + "/parameters/planck2018", "upstream": "spectrum"},
	}
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
