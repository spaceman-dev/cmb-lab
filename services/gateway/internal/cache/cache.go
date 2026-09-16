// Package cache provides a TTL cache for upstream responses.
//
// Spectrum estimation is expensive (seconds) but perfectly deterministic in its inputs, so
// caching by request signature is safe and removes the latency entirely on repeat views.
// The Store interface exists so a Redis implementation can replace the in-memory one
// without touching the proxy.
package cache

import (
	"sync"
	"time"
)

// Entry is a cached upstream response.
type Entry struct {
	Status      int
	ContentType string
	Body        []byte
	StoredAt    time.Time
}

// Store is the cache contract. Swap in Redis by implementing this.
type Store interface {
	Get(key string) (Entry, bool)
	Set(key string, entry Entry)
	Stats() (hits, misses, size int)
}

// Memory is a mutex-guarded map with TTL expiry and a size cap.
type Memory struct {
	mu      sync.RWMutex
	entries map[string]Entry
	ttl     time.Duration
	maxSize int
	hits    int
	misses  int
}

func NewMemory(ttl time.Duration, maxSize int) *Memory {
	if maxSize <= 0 {
		maxSize = 256
	}
	return &Memory{
		entries: make(map[string]Entry),
		ttl:     ttl,
		maxSize: maxSize,
	}
}

func (m *Memory) Get(key string) (Entry, bool) {
	m.mu.RLock()
	entry, ok := m.entries[key]
	m.mu.RUnlock()

	if !ok || time.Since(entry.StoredAt) > m.ttl {
		m.mu.Lock()
		if ok {
			delete(m.entries, key)
		}
		m.misses++
		m.mu.Unlock()
		return Entry{}, false
	}

	m.mu.Lock()
	m.hits++
	m.mu.Unlock()
	return entry, true
}

func (m *Memory) Set(key string, entry Entry) {
	entry.StoredAt = time.Now()

	m.mu.Lock()
	defer m.mu.Unlock()

	// Simple bound: when full, drop the oldest entry rather than grow without limit.
	if len(m.entries) >= m.maxSize {
		var oldestKey string
		var oldest time.Time
		for k, e := range m.entries {
			if oldest.IsZero() || e.StoredAt.Before(oldest) {
				oldest, oldestKey = e.StoredAt, k
			}
		}
		delete(m.entries, oldestKey)
	}

	m.entries[key] = entry
}

func (m *Memory) Stats() (int, int, int) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.hits, m.misses, len(m.entries)
}
