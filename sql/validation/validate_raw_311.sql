/*
NYC 311 Neighborhood Equity Monitor
Raw table validation queries

Purpose:
  These queries validate that the raw BigQuery table loaded correctly.

How to use:
  1. Open BigQuery.
  2. Copy one query at a time into the BigQuery SQL editor.
  3. Run the query.
  4. Record notable findings in docs/validation_notes.md.

Current sample table:
  `nyc-311-equity.nyc311_raw.service_requests_2025_01_sample`

If your table has a different name, replace the table name throughout this file.
*/


/* -------------------------------------------------------------------------
Query 1: Basic row count and unique key check

What this tells us:
  - total rows loaded
  - number of distinct service request IDs
  - whether duplicate unique_key values exist

Expected:
  duplicate_unique_key_rows should be 0.
------------------------------------------------------------------------- */

SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT unique_key) AS distinct_unique_keys,
  COUNT(*) - COUNT(DISTINCT unique_key) AS duplicate_unique_key_rows
FROM `nyc-311-equity.nyc311_raw.service_requests_2025_01_sample`;



/* -------------------------------------------------------------------------
Query 2: Raw schema check

What this tells us:
  - column names
  - raw BigQuery data types
  - nullability

Expected:
  Most raw source fields are STRING for now.
  Type conversion will happen later in dbt.
------------------------------------------------------------------------- */

SELECT
  column_name,
  data_type,
  is_nullable,
  ordinal_position
FROM `nyc-311-equity.nyc311_raw.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'service_requests_2025_01_sample'
ORDER BY ordinal_position;



/* -------------------------------------------------------------------------
Query 3: Date coverage check

What this tells us:
  - earliest created_date
  - latest created_date
  - whether created_date parses successfully as a DATETIME

Important:
  Socrata calls created_date a "Floating Timestamp", so for now we parse it
  as DATETIME rather than TIMESTAMP. We will make a final modeling decision
  in dbt later.
------------------------------------------------------------------------- */

WITH typed AS (
  SELECT
    unique_key,
    created_date,
    SAFE.PARSE_DATETIME('%Y-%m-%dT%H:%M:%E*S', created_date) AS created_datetime
  FROM `nyc-311-equity.nyc311_raw.service_requests_2025_01_sample`
)

SELECT
  MIN(created_datetime) AS min_created_datetime,
  MAX(created_datetime) AS max_created_datetime,
  COUNT(*) AS total_rows,
  COUNTIF(created_date IS NULL) AS rows_missing_created_date,
  COUNTIF(created_date IS NOT NULL AND created_datetime IS NULL) AS rows_with_unparseable_created_date
FROM typed;



/* -------------------------------------------------------------------------
Query 4: Missingness profile for key fields

What this tells us:
  Which important fields are missing frequently.

Expected:
  closed_date can be missing because some service requests are still open.
  latitude/longitude can be missing for some records.
  complaint_type, agency, borough, and created_date should usually be present.
------------------------------------------------------------------------- */

SELECT
  COUNT(*) AS total_rows,

  COUNTIF(unique_key IS NULL OR TRIM(unique_key) = '') AS missing_unique_key,
  COUNTIF(created_date IS NULL OR TRIM(created_date) = '') AS missing_created_date,
  COUNTIF(closed_date IS NULL OR TRIM(closed_date) = '') AS missing_closed_date,
  COUNTIF(agency IS NULL OR TRIM(agency) = '') AS missing_agency,
  COUNTIF(agency_name IS NULL OR TRIM(agency_name) = '') AS missing_agency_name,
  COUNTIF(complaint_type IS NULL OR TRIM(complaint_type) = '') AS missing_complaint_type,
  COUNTIF(descriptor IS NULL OR TRIM(descriptor) = '') AS missing_descriptor,
  COUNTIF(incident_zip IS NULL OR TRIM(incident_zip) = '') AS missing_incident_zip,
  COUNTIF(status IS NULL OR TRIM(status) = '') AS missing_status,
  COUNTIF(due_date IS NULL OR TRIM(due_date) = '') AS missing_due_date,
  COUNTIF(community_board IS NULL OR TRIM(community_board) = '') AS missing_community_board,
  COUNTIF(council_district IS NULL OR TRIM(council_district) = '') AS missing_council_district,
  COUNTIF(borough IS NULL OR TRIM(borough) = '') AS missing_borough,
  COUNTIF(latitude IS NULL OR TRIM(latitude) = '') AS missing_latitude,
  COUNTIF(longitude IS NULL OR TRIM(longitude) = '') AS missing_longitude
FROM `nyc-311-equity.nyc311_raw.service_requests_2025_01_sample`;



/* -------------------------------------------------------------------------
Query 5: Status values

What this tells us:
  Which service request status values are present in the sample.

Expected:
  Common values may include Closed, Open, In Progress, Pending, etc.
  We should not hard-code expected values yet until we inspect real values.
------------------------------------------------------------------------- */

SELECT
  status,
  COUNT(*) AS request_count,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percent_of_rows
FROM `nyc-311-equity.nyc311_raw.service_requests_2025_01_sample`
GROUP BY status
ORDER BY request_count DESC;



/* -------------------------------------------------------------------------
Query 6: Borough values

What this tells us:
  Which borough values exist in the raw data.

Expected:
  Usually BRONX, BROOKLYN, MANHATTAN, QUEENS, STATEN ISLAND, and possibly
  Unspecified or null values.
------------------------------------------------------------------------- */

SELECT
  borough,
  COUNT(*) AS request_count,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percent_of_rows
FROM `nyc-311-equity.nyc311_raw.service_requests_2025_01_sample`
GROUP BY borough
ORDER BY request_count DESC;



/* -------------------------------------------------------------------------
Query 7: Top agencies

What this tells us:
  Which agencies are responsible for the largest number of requests in the
  sample.
------------------------------------------------------------------------- */

SELECT
  agency,
  agency_name,
  COUNT(*) AS request_count,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percent_of_rows
FROM `nyc-311-equity.nyc311_raw.service_requests_2025_01_sample`
GROUP BY
  agency,
  agency_name
ORDER BY request_count DESC
LIMIT 20;



/* -------------------------------------------------------------------------
Query 8: Top complaint types

What this tells us:
  Which complaint types dominate the sample.

This will later help us decide whether to group complaint types into broader
categories for dashboarding.
------------------------------------------------------------------------- */

SELECT
  complaint_type,
  COUNT(*) AS request_count,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percent_of_rows
FROM `nyc-311-equity.nyc311_raw.service_requests_2025_01_sample`
GROUP BY complaint_type
ORDER BY request_count DESC
LIMIT 25;



/* -------------------------------------------------------------------------
Query 9: Date logic checks

What this tells us:
  Whether date fields parse correctly and whether there are impossible or
  suspicious date relationships.

Examples:
  - closed_date before created_date
  - due_date before created_date

Some edge cases may exist in real administrative data. The goal here is not to
delete them yet, only to identify them.
------------------------------------------------------------------------- */

WITH typed AS (
  SELECT
    unique_key,
    created_date,
    closed_date,
    due_date,
    SAFE.PARSE_DATETIME('%Y-%m-%dT%H:%M:%E*S', created_date) AS created_datetime,
    SAFE.PARSE_DATETIME('%Y-%m-%dT%H:%M:%E*S', closed_date) AS closed_datetime,
    SAFE.PARSE_DATETIME('%Y-%m-%dT%H:%M:%E*S', due_date) AS due_datetime
  FROM `nyc-311-equity.nyc311_raw.service_requests_2025_01_sample`
)

SELECT
  COUNT(*) AS total_rows,
  COUNTIF(created_date IS NOT NULL AND created_datetime IS NULL) AS unparseable_created_date,
  COUNTIF(closed_date IS NOT NULL AND closed_datetime IS NULL) AS unparseable_closed_date,
  COUNTIF(due_date IS NOT NULL AND due_datetime IS NULL) AS unparseable_due_date,
  COUNTIF(closed_datetime < created_datetime) AS closed_before_created,
  COUNTIF(due_datetime < created_datetime) AS due_before_created
FROM typed;



/* -------------------------------------------------------------------------
Query 10: Closure time summary

What this tells us:
  Among records with both created_date and closed_date, how long closure took.

This is a rough raw-data check. Later, dbt will create cleaner metrics.
------------------------------------------------------------------------- */

WITH typed AS (
  SELECT
    unique_key,
    SAFE.PARSE_DATETIME('%Y-%m-%dT%H:%M:%E*S', created_date) AS created_datetime,
    SAFE.PARSE_DATETIME('%Y-%m-%dT%H:%M:%E*S', closed_date) AS closed_datetime
  FROM `nyc-311-equity.nyc311_raw.service_requests_2025_01_sample`
),

durations AS (
  SELECT
    unique_key,
    DATETIME_DIFF(closed_datetime, created_datetime, HOUR) / 24.0 AS days_to_close
  FROM typed
  WHERE
    created_datetime IS NOT NULL
    AND closed_datetime IS NOT NULL
    AND closed_datetime >= created_datetime
)

SELECT
  COUNT(*) AS closed_records_with_valid_dates,
  ROUND(MIN(days_to_close), 2) AS min_days_to_close,
  ROUND(APPROX_QUANTILES(days_to_close, 100)[OFFSET(25)], 2) AS p25_days_to_close,
  ROUND(APPROX_QUANTILES(days_to_close, 100)[OFFSET(50)], 2) AS median_days_to_close,
  ROUND(APPROX_QUANTILES(days_to_close, 100)[OFFSET(75)], 2) AS p75_days_to_close,
  ROUND(APPROX_QUANTILES(days_to_close, 100)[OFFSET(90)], 2) AS p90_days_to_close,
  ROUND(MAX(days_to_close), 2) AS max_days_to_close
FROM durations;



/* -------------------------------------------------------------------------
Query 11: Coordinate sanity check

What this tells us:
  Whether latitude/longitude values are present and roughly plausible.

Important:
  The bounding box below is only a rough sanity check for NYC-area coordinates.
  It is not a formal geospatial validation.
------------------------------------------------------------------------- */

WITH typed AS (
  SELECT
    unique_key,
    latitude,
    longitude,
    SAFE_CAST(latitude AS FLOAT64) AS latitude_float,
    SAFE_CAST(longitude AS FLOAT64) AS longitude_float
  FROM `nyc-311-equity.nyc311_raw.service_requests_2025_01_sample`
)

SELECT
  COUNT(*) AS total_rows,
  COUNTIF(latitude IS NULL OR TRIM(latitude) = '') AS missing_latitude,
  COUNTIF(longitude IS NULL OR TRIM(longitude) = '') AS missing_longitude,
  COUNTIF(latitude IS NOT NULL AND latitude_float IS NULL) AS unparseable_latitude,
  COUNTIF(longitude IS NOT NULL AND longitude_float IS NULL) AS unparseable_longitude,
  COUNTIF(
    latitude_float IS NOT NULL
    AND longitude_float IS NOT NULL
    AND NOT (
      latitude_float BETWEEN 40.4 AND 41.0
      AND longitude_float BETWEEN -74.3 AND -73.6
    )
  ) AS coordinates_outside_rough_nyc_bounds
FROM typed;



/* -------------------------------------------------------------------------
Query 12: Requests by hour

What this tells us:
  How much of the date range the sample actually covers.

This is especially useful for capped samples. For example, a 1,000-row sample
from January 1 may only cover the first hour or two of the day.
------------------------------------------------------------------------- */

WITH typed AS (
  SELECT
    SAFE.PARSE_DATETIME('%Y-%m-%dT%H:%M:%E*S', created_date) AS created_datetime
  FROM `nyc-311-equity.nyc311_raw.service_requests_2025_01_sample`
)

SELECT
  DATETIME_TRUNC(created_datetime, HOUR) AS created_hour,
  COUNT(*) AS request_count
FROM typed
WHERE created_datetime IS NOT NULL
GROUP BY created_hour
ORDER BY created_hour;



/* -------------------------------------------------------------------------
Query 13: Potential duplicate unique keys

What this tells us:
  Which unique_key values appear more than once, if any.

Expected:
  This should return zero rows.
------------------------------------------------------------------------- */

SELECT
  unique_key,
  COUNT(*) AS row_count
FROM `nyc-311-equity.nyc311_raw.service_requests_2025_01_sample`
GROUP BY unique_key
HAVING COUNT(*) > 1
ORDER BY row_count DESC, unique_key
LIMIT 100;