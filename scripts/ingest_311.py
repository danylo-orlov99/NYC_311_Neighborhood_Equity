"""
Initial NYC 311 ingestion script.

Purpose:
    Fetch a small slice of NYC 311 service requests from the
    NYC Open Data Socrata API and write the results as a JSON file.

Example:
    python scripts/ingest_311.py \
        --start-date 2025-01-01 \
        --end-date 2025-01-02 \
        --max-rows 25

Basic Structure:
# 1. Imports
import ...

# 2. Configuration
API_ENDPOINT = "..."
SELECT_COLUMNS = [...]

# 3. Argument parsing
def parse_args():
    ...

# 4. Query-building helpers
def build_where_clause(...):
    ...

# 5. API request helper
def fetch_page(...):
    ...

# 6. Main ingestion loop
def ingest_data(...):
    ...

# 7. Entry point
def main():
    ...

if __name__ == "__main__":
    main()
"""

from __future__ import annotations

import argparse # Lets the script accept command-line options like --start-date 2025-01-01
import json # For parsing API responses and writing output as JSON
import logging # For logging progress and errors
import os # For reading the NYC_OPEN_DATA_APP_TOKEN environment variable
import sys # For sys.exit() to return an exit code from main() like return 0  # success or return 1  # error
import time # Lets us pause before retrying failed API requests
from datetime import date, datetime, timezone # For handling dates and timestamps
from pathlib import Path # For convenient file path handling
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_ENDPOINT = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

# Keep the first extract intentionally narrow.
# We can add more columns later after the pipeline works.
SELECT_COLUMNS = [
    "unique_key",
    "created_date",
    "closed_date",
    "agency",
    "agency_name",
    "complaint_type",
    "descriptor",
    "location_type",
    "incident_zip",
    "city",
    "status",
    "due_date",
    "resolution_description",
    "resolution_action_updated_date",
    "community_board",
    "council_district",
    "police_precinct",
    "borough",
    "open_data_channel_type",
    "latitude",
    "longitude",
]


# This allows the script to accept something like --start-date 2025-01-01 and automatically convert that string into a date object.
def parse_iso_date(value: str) -> date:
    """Parse a YYYY-MM-DD string into a date object."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Use YYYY-MM-DD format."
        ) from exc


# These functions allow the script to validate that --batch-size is a positive integer and that --max-rows is a non-negative integer.
def non_negative_int(value: str) -> int:
    """Validate that an argument is a non-negative integer."""
    try:
        value_int = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Value must be an integer.") from exc

    if value_int < 0:
        raise argparse.ArgumentTypeError("Value must be 0 or greater.")

    return value_int


def positive_int(value: str) -> int:
    """Validate that an argument is a positive integer."""
    try:
        value_int = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Value must be an integer.") from exc

    if value_int <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than 0.")

    return value_int

 # This function sets up the command-line arguments that the script accepts, such as --start-date, 
 # --end-date, --output, --batch-size, and --max-rows. It also includes validation for the date formats and integer values.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch NYC 311 service requests from NYC Open Data."
    )

    parser.add_argument(
        "--start-date",
        required=True, # The user must provide a start date 
        type=parse_iso_date, # Per out past defintion, it must be in YYYY-MM-DD format
        help="Inclusive start date in YYYY-MM-DD format.", # Conditional text to show in the help message for this argument
    )

    parser.add_argument(
        "--end-date", 
        required=True, # The user must also provide an end date 
        type=parse_iso_date, 
        help="Exclusive end date in YYYY-MM-DD format.",
    )

    parser.add_argument(
        "--output", 
        type=Path, # The output path will be converted to a Path object for easier file handling
        default=None, # The user can optionally provide an output path; if they don't, the script will generate a default one based on the date range
        help="Optional output file path. Defaults to data/raw/...", 
    )

    parser.add_argument(
        "--batch-size",
        type=positive_int, # The batch size must be a positive integer (greater than 0)
        default=1000,
        help="Number of rows to request per API call. Default: 1000.",
    )

    parser.add_argument(
        "--max-rows",
        type=non_negative_int, # The max rows must be a non-negative integer (0 or greater)
        default=1000,
        help=(
            "Safety cap on total rows written. Default: 1000. "
            "Use 0 for no cap."
        ),
    )

    return parser.parse_args()


# This function constructs the WHERE clause for the Socrata API query to filter records based on the created_date field.
def build_where_clause(start_date: date, end_date: date) -> str:
    """
    Build a Socrata SoQL WHERE clause.

    The start date is inclusive.
    The end date is exclusive.

    Example:
        created_date >= '2025-01-01T00:00:00'
        AND created_date < '2025-01-02T00:00:00'
    """
    return (
        f"created_date >= '{start_date.isoformat()}T00:00:00' " # Inclusive start date filter
        f"AND created_date < '{end_date.isoformat()}T00:00:00'" # Exclusive end date filter
    )


# This function is responsible for making the actual API request to fetch one page of records based on the provided parameters. 
# It includes error handling and retry logic for common HTTP errors and network issues.
def fetch_page(
    params: dict[str, Any], # The query parameters to include in the API request, such as $select, $where, $limit, and $offset
    app_token: str | None, # An optional Socrata app token 
    max_retries: int = 3, # Retry up to 3 times for errors
) -> list[dict[str, Any]]:
    """Fetch one page of records from the Socrata API."""
    url = f"{API_ENDPOINT}?{urlencode(params)}" # Construct the full URL with query parameters

    headers = {
        "Accept": "application/json",
        "User-Agent": "NYC-311-Neighborhood-Equity/0.1",
    }

    if app_token:
        headers["X-App-Token"] = app_token

    # Implementing retry logic for robustness against errors. The function will attempt to make the API request up to max_retries times if it encounters certain HTTP 
    # errors (like 429 Too Many Requests or 500 Internal Server Error) or network errors. It uses exponential backoff for retries, meaning it will wait 
    # longer between each retry attempt. If all attempts fail, it raises a RuntimeError with details about the failure. 
    for attempt in range(1, max_retries + 1):
        request = Request(url, headers=headers, method="GET")

        try:
            with urlopen(request, timeout=60) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                response_text = response.read().decode(charset)
                data = json.loads(response_text)

            if not isinstance(data, list):
                raise RuntimeError(
                    "Expected the API response to be a list of records. " # Raises an error if there is unexpected response format, like dictionalry with an error message instead of a list of records 
                    f"Received: {type(data).__name__}"
                )

            return data # If it works, returns data immediately

        # Handles HTTP errors like 429 Too Many Requests or 500 Internal Server Error with retries, and also handles network errors with retries. If it exhausts all retries, it raises a RuntimeError with details about the failure.
        except HTTPError as exc:
            retryable_status_codes = {429, 500, 502, 503, 504}

            if exc.code in retryable_status_codes and attempt < max_retries:
                sleep_seconds = min(2**attempt, 30) # Exponential backoff with a cap of 30 seconds
                logging.warning(
                    "HTTP %s from API. Retrying in %s seconds. Attempt %s/%s.",
                    exc.code,
                    sleep_seconds,
                    attempt,
                    max_retries,
                )
                time.sleep(sleep_seconds)
                continue

            error_body = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(
                f"API request failed with HTTP {exc.code}: {error_body}"
            ) from exc

        # Handles network errors like connection issues or timeouts with retries.
        except URLError as exc:
            if attempt < max_retries:
                sleep_seconds = min(2**attempt, 30)
                logging.warning(
                    "Network error: %s. Retrying in %s seconds. Attempt %s/%s.",
                    exc,
                    sleep_seconds,
                    attempt,
                    max_retries,
                )
                time.sleep(sleep_seconds)
                continue

            raise RuntimeError(f"Network request failed: {exc}") from exc

    raise RuntimeError("API request failed after all retry attempts.")


# This function coordinates the ingestion process by repeatedly calling fetch_page to retrieve batches of records and 
# writing them to an NDJSON file. It handles pagination using the $limit and $offset parameters, and it also respects 
# the max_rows limit if provided. Each record is augmented with an ingested_at timestamp before being written to the output file.
def ingest_311_data(
    start_date: date,
    end_date: date,
    output_path: Path,
    batch_size: int,
    max_rows: int | None,
) -> int:
    """
    Fetch records and write them to an NDJSON file.

    NDJSON means each line is one JSON object.
    This format is convenient for later BigQuery loading.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True) # Make sure the output directory exists, creating it if necessary

    app_token = os.getenv("NYC_OPEN_DATA_APP_TOKEN") # Looks for an optional Socrata app token in the environment variable 
    where_clause = build_where_clause(start_date=start_date, end_date=end_date)

    total_rows_written = 0 # How many rows we've written to the output file so far
    offset = 0 # How many rows we've skipped in the API query so far, used for pagination

    logging.info("Starting NYC 311 ingestion.")
    logging.info("Date range: %s to %s, end exclusive.", start_date, end_date)
    logging.info("Output path: %s", output_path)

    if app_token:
        logging.info("Using NYC_OPEN_DATA_APP_TOKEN from environment.")
    else:
        logging.info("No app token found. Proceeding without one for this small test.")

    with output_path.open("w", encoding="utf-8") as file_handle: # w is for write mode 
        while True:
            if max_rows is not None:
                remaining_rows = max_rows - total_rows_written
                if remaining_rows <= 0:
                    logging.info("Reached max row limit: %s", max_rows) # Prevent unnecessary API calls if we've already reached max_rows
                    break

                current_limit = min(batch_size, remaining_rows)
            else:
                current_limit = batch_size

            # API query parameters for pagination and filtering.
            params = {
                "$select": ",".join(SELECT_COLUMNS),
                "$where": where_clause,
                "$order": "created_date ASC, unique_key ASC", # Sort oldest to newest, and use unique_key as a tiebreaker for records with the same created_date to ensure consistent pagination
                "$limit": current_limit,
                "$offset": offset,
            }

            logging.info(
                "Fetching page: limit=%s offset=%s",
                current_limit,
                offset,
            )

            rows = fetch_page(params=params, app_token=app_token)

            if not rows:
                logging.info("No more rows returned by API.")
                break

            ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds") # Timestamp for ingestion time, added as a column to each row

            for row in rows:
                row["ingested_at"] = ingested_at
                json.dump(row, file_handle, ensure_ascii=False, sort_keys=True)
                file_handle.write("\n")

            rows_written_this_page = len(rows)
            total_rows_written += rows_written_this_page # Move the total count forward by the number of rows we just wrote
            offset += rows_written_this_page # Move the offset forward by the number of rows we just wrote

            logging.info(
                "Wrote %s rows this page; %s rows total.",
                rows_written_this_page,
                total_rows_written,
            )

            if rows_written_this_page < current_limit:
                logging.info("Last page received fewer rows than requested.")
                break

    return total_rows_written


# The main function sets up logging, parses command-line arguments, validates the date range, determines the output path, 
# and then calls the ingest_311_data function to perform the data fetching and writing. It also logs the total number of 
# rows written at the end and returns an appropriate exit code.
def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    args = parse_args()

    if args.end_date <= args.start_date:
        logging.error("--end-date must be after --start-date.")
        return 1

    output_path = args.output

    # Default output path is data/raw/311_service_requests_{start_date}_to_{end_date}.ndjson if --output is not provided
    if output_path is None:
        output_path = Path(
            "data/raw/"
            f"311_service_requests_{args.start_date.isoformat()}"
            f"_to_{args.end_date.isoformat()}.ndjson"
        )

    max_rows = None if args.max_rows == 0 else args.max_rows # No limit if max_rows is 0, otherwise use the provided max_rows value

    rows_written = ingest_311_data(
        start_date=args.start_date,
        end_date=args.end_date,
        output_path=output_path,
        batch_size=args.batch_size,
        max_rows=max_rows,
    )

    logging.info("Finished. Total rows written: %s", rows_written)

    return 0


# This allows the script to be run directly from the command line. When the script is executed, 
# it will call the main() function and exit with the returned exit code (0 for success, 1 for error).
if __name__ == "__main__":
    sys.exit(main())