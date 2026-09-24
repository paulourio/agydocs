#!/usr/bin/env python3
"""Enterprise BigQuery Schema Extraction, Dry-Run Analysis, and Ingestion.

This utility demonstrates production patterns for Google Cloud BigQuery:
1. Extracting table schemas into canonical TableFieldSchema[] JSON representation.
2. Executing deterministic dry-run query simulations to calculate scan volume and costs.
3. Storage Write API streaming ingestion structure with protobuf record serialization.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

try:
    from google.cloud import bigquery
    from google.cloud.bigquery import QueryJobConfig, SchemaField
except ImportError:
    bigquery = None  # type: ignore
    QueryJobConfig = None  # type: ignore
    SchemaField = None  # type: ignore

# Standard BigQuery on-demand analysis pricing ($6.25 per decimal TB scanned, 10 MB min).
PRICE_PER_TERABYTE_USD = Decimal("6.25")
BYTES_PER_TERABYTE = Decimal(10**12)
MIN_BILLABLE_BYTES = Decimal(10 * 1024 * 1024)


def field_to_dict(field: SchemaField) -> dict[str, Any]:
    """Recursively serializes a BigQuery SchemaField to canonical JSON dict."""
    field_dict: dict[str, Any] = {
        "name": field.name,
        "type": field.field_type,
        "mode": field.mode,
    }
    if field.description:
        field_dict["description"] = field.description

    if field.fields:
        field_dict["fields"] = [field_to_dict(sub) for sub in field.fields]

    if field.policy_tags:
        field_dict["policyTags"] = {"names": list(field.policy_tags.names)}

    return field_dict


def schema_to_json(schema: list[SchemaField], indent: int = 2) -> str:
    """Converts a BigQuery schema list into canonical TableFieldSchema[] JSON."""
    schema_list = [field_to_dict(f) for f in schema]
    return json.dumps(schema_list, indent=indent)


def export_schema(table_ref_str: str, output_path: Path | None) -> None:
    """Fetches table metadata and exports canonical schema JSON."""
    if bigquery is None:
        sys.exit("Error: 'google-cloud-bigquery' package is required. Install via pip.")

    client = bigquery.Client()
    table = client.get_table(table_ref_str)
    schema_json = schema_to_json(table.schema)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(schema_json + "\n", encoding="utf-8")
        print(f"Exported schema for {table_ref_str} to {output_path}")
    else:
        print(schema_json)


def dry_run_query(query_sql: str, project_id: str | None = None) -> None:
    """Executes a dry-run analysis for a SQL string to estimate scan size and cost."""
    if bigquery is None:
        sys.exit("Error: 'google-cloud-bigquery' package is required. Install via pip.")

    client = bigquery.Client(project=project_id)
    job_config = QueryJobConfig(
        dry_run=True,
        use_query_cache=False,
    )

    query_job = client.query(query_sql, job_config=job_config)

    bytes_scanned = Decimal(query_job.total_bytes_processed or 0)
    bytes_billed = Decimal(query_job.total_bytes_billed or 0)
    effective_billed = (
        bytes_billed
        if bytes_billed > 0
        else (
            max(bytes_scanned, MIN_BILLABLE_BYTES) if bytes_scanned > 0 else Decimal(0)
        )
    )
    gib_scanned = bytes_scanned / Decimal(1024**3)
    tb_billed = effective_billed / BYTES_PER_TERABYTE
    est_cost = tb_billed * PRICE_PER_TERABYTE_USD

    print("=== BigQuery Dry-Run Execution Analysis ===")
    print(f"Total Bytes Processed : {bytes_scanned:,} bytes ({gib_scanned:.4f} GiB)")
    print(f"Total Bytes Billed    : {effective_billed:,} bytes")
    print(f"Estimated Scan Cost   : ${est_cost:.4f} USD (@ $6.25 / TB)")

    if query_job.schema:
        print(f"Output Columns        : {len(query_job.schema)}")
        for col in query_job.schema:
            print(f"  - {col.name}: {col.field_type} ({col.mode})")


def storage_write_api_demo() -> None:
    """Demonstrates Storage Write API initialization and stream configuration."""
    print("=== Storage Write API Default Stream Ingestion Outline ===")
    outline = """
from google.cloud import bigquery_storage_v1
from google.cloud.bigquery_storage_v1 import types
from google.protobuf import descriptor_pb2

# 1. Initialize client
write_client = bigquery_storage_v1.BigQueryWriteClient()

# 2. Configure parent table and default stream (immediate commit, exactly-once)
parent = write_client.table_path(project_id, dataset_id, table_id)
stream_name = f"{parent}/streams/_default"

# 3. Create request stream using proto2 / proto3 compiled descriptors
request_template = types.AppendRowsRequest()
request_template.write_stream = stream_name

proto_schema = types.ProtoSchema()
proto_descriptor = descriptor_pb2.DescriptorProto()
# ... serialize protobuf descriptor ...
proto_schema.proto_descriptor = proto_descriptor
request_template.proto_rows.writer_schema = proto_schema

# 4. Stream rows using append_rows() bidirectional stream
# responses = write_client.append_rows(iter([request_template, row_request]))
"""
    print(outline)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enterprise BigQuery Schema and Dry-Run Utility",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: export-schema
    schema_parser = subparsers.add_parser(
        "export-schema", help="Export table schema to JSON"
    )
    schema_parser.add_argument("table", help="Table identifier (project.dataset.table)")
    schema_parser.add_argument(
        "-o", "--output", type=Path, help="Target JSON output file path"
    )

    # Subcommand: dry-run
    dry_parser = subparsers.add_parser("dry-run", help="Simulate query execution cost")
    query_group = dry_parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("-q", "--query", help="Raw SQL query string")
    query_group.add_argument("-f", "--file", type=Path, help="Path to SQL file")
    dry_parser.add_argument("-p", "--project", help="GCP project ID override")

    # Subcommand: storage-write-info
    subparsers.add_parser(
        "storage-write-info",
        help="Print Storage Write API configuration patterns",
    )

    args = parser.parse_args()

    if args.command == "export-schema":
        export_schema(args.table, args.output)
    elif args.command == "dry-run":
        if args.file:
            sql_content = args.file.read_text(encoding="utf-8")
        else:
            sql_content = args.query
        dry_run_query(sql_content, args.project)
    elif args.command == "storage-write-info":
        storage_write_api_demo()


if __name__ == "__main__":
    main()
