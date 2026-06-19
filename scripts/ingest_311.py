"""
Initial NYC 311 ingestion script.

Purpose:
    Fetch a small, date-bounded slice of NYC 311 service requests from the
    NYC Open Data Socrata API and write the results as newline-delimited JSON.

This script intentionally avoids pandas for now. The goal is extraction, not analysis.

Example:
    python scripts/ingest_311.py \
        --start-date 2025-01-01 \
        --end-date 2025-01-02 \
        --max-rows 25
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
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


def parse_iso_date(value: str) -> date:
    """Parse a YYYY-MM-DD string into a date object."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Use YYYY-MM-DD format."
        ) from exc


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch NYC 311 service requests from NYC Open Data."
    )

    parser.add_argument(
        "--start-date",
        required=True,
        type=parse_iso_date,
        help="Inclusive start date in YYYY-MM-DD format.",
    )

    parser.add_argument(
        "--end-date",
        required=True,
        type=parse_iso_date,
        help="Exclusive end date in YYYY-MM-DD format.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output file path. Defaults to data/raw/...",
    )

    parser.add_argument(
        "--batch-size",
        type=positive_int,
        default=1000,
        help="Number of rows to request per API call. Default: 1000.",
    )

    parser.add_argument(
        "--max-rows",
        type=non_negative_int,
        default=1000,
        help=(
            "Safety cap on total rows written. Default: 1000. "
            "Use 0 for no cap."
        ),
    )

    return parser.parse_args()


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
        f"created_date >= '{start_date.isoformat()}T00:00:00' "
        f"AND created_date < '{end_date.isoformat()}T00:00:00'"
    )


def fetch_page(
    params: dict[str, Any],
    app_token: str | None,
    max_retries: int = 3,
) -> list[dict[str, Any]]:
    """Fetch one page of records from the Socrata API."""
    url = f"{API_ENDPOINT}?{urlencode(params)}"

    headers = {
        "Accept": "application/json",
        "User-Agent": "NYC-311-Neighborhood-Equity/0.1",
    }

    if app_token:
        headers["X-App-Token"] = app_token

    for attempt in range(1, max_retries + 1):
        request = Request(url, headers=headers, method="GET")

        try:
            with urlopen(request, timeout=60) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                response_text = response.read().decode(charset)
                data = json.loads(response_text)

            if not isinstance(data, list):
                raise RuntimeError(
                    "Expected the API response to be a list of records. "
                    f"Received: {type(data).__name__}"
                )

            return data

        except HTTPError as exc:
            retryable_status_codes = {429, 500, 502, 503, 504}

            if exc.code in retryable_status_codes and attempt < max_retries:
                sleep_seconds = min(2**attempt, 30)
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
    output_path.parent.mkdir(parents=True, exist_ok=True)

    app_token = os.getenv("NYC_OPEN_DATA_APP_TOKEN")
    where_clause = build_where_clause(start_date=start_date, end_date=end_date)

    total_rows_written = 0
    offset = 0

    logging.info("Starting NYC 311 ingestion.")
    logging.info("Date range: %s to %s, end exclusive.", start_date, end_date)
    logging.info("Output path: %s", output_path)

    if app_token:
        logging.info("Using NYC_OPEN_DATA_APP_TOKEN from environment.")
    else:
        logging.info("No app token found. Proceeding without one for this small test.")

    with output_path.open("w", encoding="utf-8") as file_handle:
        while True:
            if max_rows is not None:
                remaining_rows = max_rows - total_rows_written
                if remaining_rows <= 0:
                    logging.info("Reached max row limit: %s", max_rows)
                    break

                current_limit = min(batch_size, remaining_rows)
            else:
                current_limit = batch_size

            params = {
                "$select": ",".join(SELECT_COLUMNS),
                "$where": where_clause,
                "$order": "created_date ASC, unique_key ASC",
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

            ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

            for row in rows:
                row["ingested_at"] = ingested_at
                json.dump(row, file_handle, ensure_ascii=False, sort_keys=True)
                file_handle.write("\n")

            rows_written_this_page = len(rows)
            total_rows_written += rows_written_this_page
            offset += rows_written_this_page

            logging.info(
                "Wrote %s rows this page; %s rows total.",
                rows_written_this_page,
                total_rows_written,
            )

            if rows_written_this_page < current_limit:
                logging.info("Last page received fewer rows than requested.")
                break

    return total_rows_written


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

    if output_path is None:
        output_path = Path(
            "data/raw/"
            f"311_service_requests_{args.start_date.isoformat()}"
            f"_to_{args.end_date.isoformat()}.ndjson"
        )

    max_rows = None if args.max_rows == 0 else args.max_rows

    rows_written = ingest_311_data(
        start_date=args.start_date,
        end_date=args.end_date,
        output_path=output_path,
        batch_size=args.batch_size,
        max_rows=max_rows,
    )

    logging.info("Finished. Total rows written: %s", rows_written)

    return 0


if __name__ == "__main__":
    sys.exit(main())