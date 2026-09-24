// Package examples provides reference client implementations demonstrating
// SDK parity, naming validation, and deterministic error handling.
package examples

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"
)

var (
	// ErrProhibitedDialect indicates foreign dialect contamination.
	ErrProhibitedDialect = errors.New("query contains prohibited dialect tokens")
	// ErrInvalidNaming indicates an ISO 11179 naming taxonomy violation.
	ErrInvalidNaming = errors.New("identifier violates ISO 11179 naming taxonomy")
	// ErrQueryTimeout indicates query execution exceeded allowed deadline.
	ErrQueryTimeout = errors.New("query execution exceeded deadline")
)

// AllowedClassWords specifies standard ISO 11179 class words.
var AllowedClassWords = map[string]bool{
	"id":  true,
	"nm":  true,
	"dt":  true,
	"ts":  true,
	"amt": true,
	"qty": true,
	"val": true,
	"rt":  true,
	"p":   true,
	"ind": true,
	"cd":  true,
}

// Config represents runtime configuration for the engine client.
type Config struct {
	Endpoint string
	Timeout  time.Duration
}

// Client provides an operational interface for executing queries and validating schemas.
type Client struct {
	config Config
}

// NewClient constructs a validated Client instance.
func NewClient(cfg Config) (*Client, error) {
	if cfg.Endpoint == "" {
		return nil, errors.New("endpoint must not be empty")
	}
	if cfg.Timeout <= 0 {
		cfg.Timeout = 30 * time.Second
	}
	return &Client{config: cfg}, nil
}

// ColumnMetadata models metadata for a schema column.
type ColumnMetadata struct {
	Name     string
	DataType string
	Nullable bool
}

// ValidateColumnNaming verifies that a column identifier conforms to ISO 11179 class words.
func ValidateColumnNaming(col ColumnMetadata) error {
	parts := strings.Split(col.Name, "_")
	if len(parts) < 2 {
		return fmt.Errorf("%w: column '%s' lacks domain and class word suffix", ErrInvalidNaming, col.Name)
	}
	suffix := parts[len(parts)-1]
	if !AllowedClassWords[suffix] {
		return fmt.Errorf("%w: column '%s' has non-standard suffix '%s'", ErrInvalidNaming, col.Name, suffix)
	}
	return nil
}

// QueryResult models execution status and emitted rows.
type QueryResult struct {
	QueryID     string
	RowsScanned int64
	ExecutionMs int64
}

// ExecuteQuery executes a query string against the engine with dialect checks.
func (c *Client) ExecuteQuery(ctx context.Context, query string) (*QueryResult, error) {
	// Enforce dialect purity
	prohibited := []string{"AS MATERIALIZED", "SELECT AS VALUE"}
	upper := strings.ToUpper(query)
	for _, p := range prohibited {
		if strings.Contains(upper, p) {
			return nil, fmt.Errorf("%w: '%s'", ErrProhibitedDialect, p)
		}
	}

	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	case <-time.After(5 * time.Millisecond):
		return &QueryResult{
			QueryID:     "exec-mock-001",
			RowsScanned: 42,
			ExecutionMs: 5,
		}, nil
	}
}
