package gate

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
)

// Cache manages thread-safe caching of audit reports across runs and memory.
type Cache struct {
	mu       sync.RWMutex
	dir      string
	enabled  bool
	memCache map[string]*AuditReport
}

// NewCache creates a new Cache instance. If dir is non-empty and enabled is true,
// it uses the directory for persistent storage.
func NewCache(dir string, enabled bool) *Cache {
	return &Cache{
		dir:      dir,
		enabled:  enabled,
		memCache: make(map[string]*AuditReport),
	}
}

func (c *Cache) key(content []byte, profile string) string {
	h := sha256.New()
	h.Write(content)
	h.Write([]byte{0})
	h.Write([]byte(profile))
	return hex.EncodeToString(h.Sum(nil))
}

// Get retrieves a cached audit report if present.
func (c *Cache) Get(content []byte, profile string) (*AuditReport, bool) {
	if !c.enabled {
		return nil, false
	}
	k := c.key(content, profile)

	c.mu.RLock()
	rep, ok := c.memCache[k]
	c.mu.RUnlock()
	if ok {
		return rep, true
	}

	if c.dir == "" {
		return nil, false
	}

	cacheFile := filepath.Join(c.dir, k+".json")
	data, err := os.ReadFile(cacheFile)
	if err != nil {
		return nil, false
	}

	var report AuditReport
	if err := json.Unmarshal(data, &report); err != nil {
		return nil, false
	}

	c.mu.Lock()
	c.memCache[k] = &report
	c.mu.Unlock()

	return &report, true
}

// Put stores an audit report in the cache.
func (c *Cache) Put(content []byte, profile string, report *AuditReport) {
	if !c.enabled {
		return
	}
	k := c.key(content, profile)

	c.mu.Lock()
	c.memCache[k] = report
	c.mu.Unlock()

	if c.dir == "" {
		return
	}

	_ = os.MkdirAll(c.dir, 0755)
	data, err := json.Marshal(report)
	if err != nil {
		return
	}

	cacheFile := filepath.Join(c.dir, k+".json")
	_ = os.WriteFile(cacheFile, data, 0644)
}
