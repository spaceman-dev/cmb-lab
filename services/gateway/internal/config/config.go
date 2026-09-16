// Package config loads gateway settings from the environment.
package config

import (
	"os"
	"strconv"
	"time"
)

// Config holds everything the gateway needs to route and protect traffic.
type Config struct {
	Port string

	CatalogURL    string
	SpectrumURL   string
	CosmologyURL  string
	AnomalyURL    string
	LiteratureURL string
	SkymapURL     string
	TutorURL      string
	ChatURL       string
	PlaygroundURL string

	// CacheTTL controls how long successful upstream responses are reused.
	// Spectrum estimates are deterministic in their inputs, so caching is free correctness-wise.
	CacheTTL time.Duration

	// RateLimit is the sustained requests/second allowed per client IP.
	RateLimit float64
	RateBurst int

	UpstreamTimeout time.Duration
	AllowedOrigins  []string

	// StaticDir, when set, makes the gateway also serve the built frontend from that
	// directory. Container platforms expose a single port, so this collapses the
	// frontend and the API onto one listener. Empty in local development, where Vite
	// serves the frontend itself.
	StaticDir string
}

func Load() Config {
	return Config{
		Port:            env("GATEWAY_PORT", "8080"),
		CatalogURL:      env("CATALOG_URL", "http://localhost:8001"),
		SpectrumURL:     env("SPECTRUM_URL", "http://localhost:8003"),
		CosmologyURL:    env("COSMOLOGY_URL", "http://localhost:8004"),
		AnomalyURL:      env("ANOMALY_URL", "http://localhost:8005"),
		LiteratureURL:   env("LITERATURE_URL", "http://localhost:8006"),
		SkymapURL:       env("SKYMAP_URL", "http://localhost:8007"),
		TutorURL:        env("TUTOR_URL", "http://localhost:8008"),
		ChatURL:         env("CHAT_URL", "http://localhost:8009"),
		PlaygroundURL:   env("PLAYGROUND_URL", "http://localhost:8010"),
		CacheTTL:        envDuration("GATEWAY_CACHE_TTL", 10*time.Minute),
		RateLimit:       envFloat("GATEWAY_RATE_LIMIT", 20),
		RateBurst:       envInt("GATEWAY_RATE_BURST", 40),
		UpstreamTimeout: envDuration("GATEWAY_UPSTREAM_TIMEOUT", 120*time.Second),
		StaticDir:       env("STATIC_DIR", ""),
		AllowedOrigins: []string{
			"http://localhost:5173",
			"http://127.0.0.1:5173",
		},
	}
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func envInt(key string, fallback int) int {
	if v, err := strconv.Atoi(os.Getenv(key)); err == nil {
		return v
	}
	return fallback
}

func envFloat(key string, fallback float64) float64 {
	if v, err := strconv.ParseFloat(os.Getenv(key), 64); err == nil {
		return v
	}
	return fallback
}

func envDuration(key string, fallback time.Duration) time.Duration {
	if v, err := time.ParseDuration(os.Getenv(key)); err == nil {
		return v
	}
	return fallback
}
