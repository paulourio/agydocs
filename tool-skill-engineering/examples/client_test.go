package examples

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestNewClient(t *testing.T) {
	_, err := NewClient(Config{})
	if err == nil {
		t.Fatal("expected error for empty endpoint")
	}

	cli, err := NewClient(Config{Endpoint: "mock://localhost:9000"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cli.config.Timeout != 30*time.Second {
		t.Errorf("expected default timeout 30s, got %v", cli.config.Timeout)
	}
}

func TestValidateColumnNaming(t *testing.T) {
	tests := []struct {
		name    string
		col     ColumnMetadata
		wantErr bool
	}{
		{
			name:    "valid user_id",
			col:     ColumnMetadata{Name: "user_id", DataType: "INT64"},
			wantErr: false,
		},
		{
			name:    "valid total_amt",
			col:     ColumnMetadata{Name: "total_amt", DataType: "NUMERIC"},
			wantErr: false,
		},
		{
			name:    "valid event_ts",
			col:     ColumnMetadata{Name: "event_ts", DataType: "TIMESTAMP"},
			wantErr: false,
		},
		{
			name:    "invalid missing suffix",
			col:     ColumnMetadata{Name: "user", DataType: "STRING"},
			wantErr: true,
		},
		{
			name:    "invalid non-standard suffix",
			col:     ColumnMetadata{Name: "user_name", DataType: "STRING"},
			wantErr: true, // Should be user_nm
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := ValidateColumnNaming(tt.col)
			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateColumnNaming(%s) error = %v, wantErr %v", tt.col.Name, err, tt.wantErr)
			}
		})
	}
}

func TestExecuteQuery(t *testing.T) {
	cli, err := NewClient(Config{Endpoint: "mock://localhost:9000"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	t.Run("prohibited dialect rejection", func(t *testing.T) {
		_, err := cli.ExecuteQuery(context.Background(), "WITH t AS MATERIALIZED (SELECT 1)")
		if !errors.Is(err, ErrProhibitedDialect) {
			t.Fatalf("expected ErrProhibitedDialect, got %v", err)
		}
	})

	t.Run("clean query execution", func(t *testing.T) {
		res, err := cli.ExecuteQuery(context.Background(), "SELECT user_id, event_ts FROM events_fact")
		if err != nil {
			t.Fatalf("unexpected execution error: %v", err)
		}
		if res.RowsScanned != 42 {
			t.Errorf("expected 42 rows, got %d", res.RowsScanned)
		}
	})
}
