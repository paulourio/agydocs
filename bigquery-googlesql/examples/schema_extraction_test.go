package main

import (
	"encoding/json"
	"testing"

	"cloud.google.com/go/bigquery"
)

func TestSchemaToJSONFields(t *testing.T) {
	schema := bigquery.Schema{
		{
			Name:        "event_id",
			Type:        bigquery.StringFieldType,
			Required:    true,
			Description: "Primary UUID event key",
		},
		{
			Name:     "event_ts",
			Type:     bigquery.TimestampFieldType,
			Required: true,
		},
		{
			Name:     "user_id",
			Type:     bigquery.IntegerFieldType,
			Repeated: false,
		},
		{
			Name:     "line_items",
			Type:     bigquery.RecordFieldType,
			Repeated: true,
			Schema: bigquery.Schema{
				{
					Name:     "item_id",
					Type:     bigquery.StringFieldType,
					Required: true,
				},
				{
					Name:     "price_amt",
					Type:     bigquery.NumericFieldType,
					Required: true,
				},
			},
		},
	}

	jsonBytes, err := schema.ToJSONFields()
	if err != nil {
		t.Fatalf("Failed to serialize schema to JSON: %v", err)
	}

	var parsed []map[string]any
	if err := json.Unmarshal(jsonBytes, &parsed); err != nil {
		t.Fatalf("Serialized schema is not valid JSON: %v", err)
	}

	if len(parsed) != 4 {
		t.Errorf("Expected 4 fields, got %d", len(parsed))
	}

	if parsed[0]["name"] != "event_id" || parsed[0]["type"] != "STRING" || parsed[0]["mode"] != "REQUIRED" {
		t.Errorf("Unexpected field 0 properties: %v", parsed[0])
	}

	recordField := parsed[3]
	if recordField["name"] != "line_items" || recordField["type"] != "RECORD" || recordField["mode"] != "REPEATED" {
		t.Errorf("Unexpected record field properties: %v", recordField)
	}

	subfields, ok := recordField["fields"].([]any)
	if !ok || len(subfields) != 2 {
		t.Errorf("Expected 2 subfields in record, got %v", recordField["fields"])
	}
}
