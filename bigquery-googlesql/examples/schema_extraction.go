// Package main implements a production-grade BigQuery schema extractor,
// dry-run cost calculator, and optional live query execution harness using
// the official Google Cloud BigQuery Go SDK (cloud.google.com/go/bigquery).
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"os"
	"time"

	"cloud.google.com/go/bigquery"
	"google.golang.org/api/iterator"
)

func main() {
	projectID := flag.String("project", "", "GCP Project ID")
	datasetID := flag.String("dataset", "", "BigQuery Dataset ID")
	tableID := flag.String("table", "", "BigQuery Table ID")
	outputFile := flag.String("output", "schema.json", "Output JSON schema file path")
	runLive := flag.Bool("run-live", false, "Execute live query against BigQuery (incurs compute costs)")
	demoWrite := flag.Bool("demo-write-api", false, "Display Storage Write API ManagedWriter pattern for Go")
	flag.Parse()

	if *demoWrite {
		storageWriteAPIDemo()
		return
	}

	if *projectID == "" || *datasetID == "" || *tableID == "" {
		fmt.Println("Usage: go run schema_extraction.go -project=<proj> -dataset=<ds> -table=<tbl> [-output=schema.json] [-run-live] [-demo-write-api]")
		os.Exit(1)
	}

	ctx := context.Background()
	client, err := bigquery.NewClient(ctx, *projectID)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error creating BigQuery client: %v\n", err)
		os.Exit(1)
	}
	defer client.Close()

	// 1. Schema Extraction to Canonical JSON
	tableRef := client.Dataset(*datasetID).Table(*tableID)
	meta, err := tableRef.Metadata(ctx)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error fetching table metadata: %v\n", err)
		os.Exit(1)
	}

	jsonBytes, err := meta.Schema.ToJSONFields()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error converting schema to JSON: %v\n", err)
		os.Exit(1)
	}

	if err := os.WriteFile(*outputFile, jsonBytes, 0644); err != nil {
		fmt.Fprintf(os.Stderr, "Error saving schema file: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Extracted schema saved to %s (%d fields)\n", *outputFile, len(meta.Schema))

	// 2. Perform Cost-Estimation Dry Run
	querySQL := fmt.Sprintf("SELECT COUNT(*) AS total_row_qty FROM `%s.%s.%s`", *projectID, *datasetID, *tableID)
	query := client.Query(querySQL)
	query.DryRun = true

	// Invariant: Dry run queries must call Run(), never Read()
	job, err := query.Run(ctx)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error submitting dry run: %v\n", err)
		os.Exit(1)
	}

	// Invariant: Dry run jobs are not recorded in job history; call LastStatus()
	status := job.LastStatus()
	if status.Err() != nil {
		fmt.Fprintf(os.Stderr, "Dry run failed: %v\n", status.Err())
		os.Exit(1)
	}

	stats, ok := status.Statistics.Details.(*bigquery.QueryStatistics)
	if ok {
		fmt.Printf("Dry Run Successful:\n")
		fmt.Printf("  Total Bytes Processed: %d bytes (%.2f MB)\n",
			stats.TotalBytesProcessed, float64(stats.TotalBytesProcessed)/(1024*1024))
		fmt.Printf("  Total Bytes Billed:    %d bytes (%.2f MB)\n",
			stats.TotalBytesBilled, float64(stats.TotalBytesBilled)/(1024*1024))
	}

	// 3. Optional Live Execution with Context Timeout and Iterator Paging
	if !*runLive {
		fmt.Println("Skipping live query execution (pass -run-live to execute).")
		return
	}

	execCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	liveQuery := client.Query(querySQL)
	liveQuery.Priority = bigquery.BatchPriority
	liveQuery.Labels = map[string]string{
		"tool": "schema_extractor",
		"env":  "production",
	}

	it, err := liveQuery.Read(execCtx)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error executing live query: %v\n", err)
		os.Exit(1)
	}

	for {
		var row []bigquery.Value
		err := it.Next(&row)
		if errors.Is(err, iterator.Done) {
			break
		}
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error reading row: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("Live Query Output: %v\n", row)
	}
}

// storageWriteAPIDemo documents the Go Storage Write API pattern using managedwriter.
func storageWriteAPIDemo() {
	fmt.Println("=== Storage Write API ManagedWriter Ingestion Pattern (Go) ===")
	outline := `
// Official Go Storage Write API pattern via cloud.google.com/go/bigquery/storage/managedwriter:
//
// 1. Initialize ManagedWriter client
//    mwClient, err := managedwriter.NewClient(ctx, projectID)
//    defer mwClient.Close()
//
// 2. Configure ManagedStream (Default stream for at-least-once / immediate availability)
//    ms, err := mwClient.NewManagedStream(ctx,
//        managedwriter.WithDestinationTable(managedwriter.TableReference{
//            ProjectID: projectID,
//            DatasetID: datasetID,
//            TableID:   tableID,
//        }),
//        managedwriter.WithType(managedwriter.DefaultStream),
//        managedwriter.WithSchemaDescriptor(descriptorProto),
//    )
//    defer ms.Close()
//
// 3. Append serialized protobuf rows concurrently
//    result, err := ms.AppendRows(ctx, [][]byte{rowBytes1, rowBytes2})
//    recvOffset, err := result.GetResult(ctx)
`
	fmt.Println(outline)
}
