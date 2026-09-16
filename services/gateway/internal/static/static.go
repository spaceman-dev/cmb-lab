package static

import (
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

// Handler serves a built single-page app from dir.
//
// Container platforms (Hugging Face Spaces, Cloud Run, Fly, Render) expose exactly one
// port, so in those deployments the gateway has to serve the frontend as well as proxy the
// API. When dir is empty or missing, New returns nil and the caller keeps its API-only
// 404 behaviour — which is what happens in local development, where Vite serves the app.
func New(dir string) http.Handler {
	if dir == "" {
		return nil
	}
	if info, err := os.Stat(filepath.Join(dir, "index.html")); err != nil || info.IsDir() {
		return nil
	}

	files := http.FileServer(http.Dir(dir))
	index := filepath.Join(dir, "index.html")

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		clean := filepath.Clean(r.URL.Path)

		// filepath.Clean strips ".." segments, but reject anything that still looks like
		// traversal before it reaches the filesystem.
		if strings.Contains(clean, "..") {
			http.Error(w, "invalid path", http.StatusBadRequest)
			return
		}

		path := filepath.Join(dir, clean)
		if info, err := os.Stat(path); err == nil && !info.IsDir() {
			// Vite emits content-hashed filenames under /assets, so they can be cached
			// indefinitely. index.html must never be, or clients pin to a stale build.
			if strings.HasPrefix(clean, "/assets/") {
				w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
			}
			files.ServeHTTP(w, r)
			return
		}

		// Unknown path with no file behind it: hand back the SPA shell and let the
		// client router decide. Without this, a deep link like /#inference 404s on reload.
		w.Header().Set("Cache-Control", "no-cache")
		http.ServeFile(w, r, index)
	})
}
