"""
Load a local NYC 311 NDJSON extract into BigQuery.

This script is the second step in the pipeline:

    NYC Open Data API
        -> local NDJSON file
        -> BigQuery raw table

The ingestion script created the local NDJSON file.
This script loads that file into BigQuery.

Example PowerShell command:

    python scripts/load_to_bigquery.py `
        --project-id nyc-311-equity `
        --dataset nyc311_raw `
        --table service_requests_test_25_rows `
        --input-file data/raw/311_service_requests_2025-01-01_to_2025-01-02.ndjson `
        --location US `
        --write-mode truncate

Important design choice:
    The raw table stores most fields as STRING.

    This is intentional. In a modern data pipeline, the raw layer should
    preserve the source data with minimal transformation. Later, dbt will
    handle type casting, date parsing, cleaning, and derived metrics.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from google.cloud import bigquery


# This schema should match the columns produced by scripts/ingest_311.py.
#
# We keep the raw table simple:
#   - source fields are loaded as STRING
#   - ingested_at is also STRING for now
#
# Later, dbt will create clean typed columns such as:
#   - created_timestamp
#   - closed_timestamp
#   - latitude_float
#   - longitude_float
#   - days_to_close
#   - is_closed
#   - is_late
RAW_311_SCHEMA = [
    bigquery.SchemaField("unique_key", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("created_date", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("closed_date", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("agency", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("agency_name", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("complaint_type", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("descriptor", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("location_type", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("incident_zip", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("city", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("due_date", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("resolution_description", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("resolution_action_updated_date", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("community_board", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("council_district", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("police_precinct", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("borough", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("open_data_channel_type", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("latitude", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("longitude", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("ingested_at", "STRING", mode="NULLABLE"),
]


def parse_args() -> argparse.Namespace:
    """
    Define the command-line interface for this script.

    This lets us reuse the script for different files and tables instead of
    hard-coding one filename or one BigQuery table.
    """
    parser = argparse.ArgumentParser(
        description="Load a local NYC 311 NDJSON file into BigQuery."
    )

    parser.add_argument(
        "--project-id",
        required=True,
        help="Google Cloud project ID, for example: nyc-311-equity.",
    )

    parser.add_argument(
        "--dataset",
        default="nyc311_raw",
        help="BigQuery dataset name. Default: nyc311_raw.",
    )

    parser.add_argument(
        "--table",
        required=True,
        help="BigQuery destination table name.",
    )

    parser.add_argument(
        "--input-file",
        required=True,
        type=Path,
        help="Path to the local NDJSON file created by the ingestion script.",
    )

    parser.add_argument(
        "--location",
        default="US",
        help="BigQuery location. Default: US.",
    )

    parser.add_argument(
        "--write-mode",
        choices=["truncate", "append", "empty"],
        default="truncate",
        help=(
            "How to write to the table. "
            "truncate = replace table contents; "
            "append = add rows; "
            "empty = fail if table already has data. "
            "Default: truncate."
        ),
    )

    return parser.parse_args()


def get_write_disposition(write_mode: str) -> str:
    """
    Convert our friendly command-line option into BigQuery's terminology.

    BigQuery calls this a write disposition.

    For early testing, truncate is useful because we can rerun the script
    repeatedly and get the same table instead of accidentally duplicating rows.
    """
    if write_mode == "truncate":
        return bigquery.WriteDisposition.WRITE_TRUNCATE

    if write_mode == "append":
        return bigquery.WriteDisposition.WRITE_APPEND

    if write_mode == "empty":
        return bigquery.WriteDisposition.WRITE_EMPTY

    raise ValueError(f"Unsupported write mode: {write_mode}")


def create_dataset_if_needed(
    client: bigquery.Client,
    project_id: str,
    dataset_name: str,
    location: str,
) -> None:
    """
    Create the BigQuery dataset if it does not already exist.

    A BigQuery dataset is a container for tables.

    In this project, nyc311_raw will hold source-like raw tables.
    Later, dbt will create staging and mart tables in separate datasets.
    """
    dataset_id = f"{project_id}.{dataset_name}"

    dataset = bigquery.Dataset(dataset_id)
    dataset.location = location

    client.create_dataset(dataset, exists_ok=True)

    logging.info("Dataset is ready: %s", dataset_id)


def load_file_to_table(
    client: bigquery.Client,
    project_id: str,
    dataset_name: str,
    table_name: str,
    input_file: Path,
    location: str,
    write_disposition: str,
) -> bigquery.LoadJob:
    """
    Load the local NDJSON file into a BigQuery table.

    This is a batch load job.

    It is not streaming, and it is not inserting rows one by one.
    That is good for our project because batch loading is simple,
    repeatable, and appropriate for raw extracts.
    """
    table_id = f"{project_id}.{dataset_name}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        schema=RAW_311_SCHEMA,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=write_disposition,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
        ignore_unknown_values=False,
        max_bad_records=0,
    )

    logging.info("Loading file into BigQuery.")
    logging.info("Input file: %s", input_file)
    logging.info("Destination table: %s", table_id)

    with input_file.open("rb") as source_file:
        load_job = client.load_table_from_file(
            source_file,
            table_id,
            location=location,
            job_config=job_config,
        )

    logging.info("Started BigQuery load job: %s", load_job.job_id)

    # Wait for the job to finish.
    load_job.result()

    logging.info("Load job finished.")

    return load_job


def run_validation_query(
    client: bigquery.Client,
    project_id: str,
    dataset_name: str,
    table_name: str,
    location: str,
) -> None:
    """
    Run a simple validation query after loading.

    This does not prove the data is analytically perfect.
    It only confirms that the load worked and that basic row counts look sane.
    """
    table_id = f"{project_id}.{dataset_name}.{table_name}"

    query = f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT unique_key) AS distinct_unique_keys,
            MIN(created_date) AS min_created_date,
            MAX(created_date) AS max_created_date,
            COUNTIF(closed_date IS NULL) AS rows_missing_closed_date,
            COUNTIF(latitude IS NULL OR longitude IS NULL) AS rows_missing_coordinates
        FROM `{table_id}`
    """

    logging.info("Running validation query.")

    query_job = client.query(query, location=location)
    rows = list(query_job.result())

    if not rows:
        logging.warning("Validation query returned no rows.")
        return

    row = rows[0]

    logging.info("Validation results:")
    logging.info("  total_rows: %s", row.total_rows)
    logging.info("  distinct_unique_keys: %s", row.distinct_unique_keys)
    logging.info("  min_created_date: %s", row.min_created_date)
    logging.info("  max_created_date: %s", row.max_created_date)
    logging.info("  rows_missing_closed_date: %s", row.rows_missing_closed_date)
    logging.info("  rows_missing_coordinates: %s", row.rows_missing_coordinates)


def main() -> int:
    """
    Main script flow.

    The sequence is:

        1. Parse command-line arguments.
        2. Confirm the input file exists.
        3. Connect to BigQuery.
        4. Create the dataset if needed.
        5. Load the file.
        6. Validate the loaded table.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    args = parse_args()

    if not args.input_file.exists():
        logging.error("Input file does not exist: %s", args.input_file)
        return 1

    if not args.input_file.is_file():
        logging.error("Input path is not a file: %s", args.input_file)
        return 1

    write_disposition = get_write_disposition(args.write_mode)

    # This client uses our local Application Default Credentials.
    # We already created those with:
    #   gcloud.cmd auth application-default login
    client = bigquery.Client(project=args.project_id)

    create_dataset_if_needed(
        client=client,
        project_id=args.project_id,
        dataset_name=args.dataset,
        location=args.location,
    )

    load_job = load_file_to_table(
        client=client,
        project_id=args.project_id,
        dataset_name=args.dataset,
        table_name=args.table,
        input_file=args.input_file,
        location=args.location,
        write_disposition=write_disposition,
    )

    logging.info("Rows loaded according to BigQuery job: %s", load_job.output_rows)

    run_validation_query(
        client=client,
        project_id=args.project_id,
        dataset_name=args.dataset,
        table_name=args.table,
        location=args.location,
    )

    logging.info("Done.")

    return 0


if __name__ == "__main__":
    sys.exit(main())