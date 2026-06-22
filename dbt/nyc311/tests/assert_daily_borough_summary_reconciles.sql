/*
Test: assert_daily_borough_summary_reconciles

Purpose:
  Confirm that the daily borough mart reconciles to the staging model.

Pass condition:
  This query returns zero rows.

Fail condition:
  This query returns one row showing a mismatch between staging row count
  and SUM(request_count) in the mart.
*/

WITH staging AS (
    SELECT
        COUNT(*) AS staging_request_count
    FROM {{ ref('stg_311_service_requests') }}
),

mart AS (
    SELECT
        SUM(request_count) AS mart_request_count
    FROM {{ ref('mart_311_daily_borough_summary') }}
)

SELECT
    staging.staging_request_count,
    mart.mart_request_count,
    staging.staging_request_count - mart.mart_request_count AS difference
FROM staging
CROSS JOIN mart
WHERE staging.staging_request_count != mart.mart_request_count