/*
Test: assert_agency_performance_reconciles

Purpose:
  Confirm that the agency performance mart reconciles to the staging model.

Pass condition:
  This query returns zero rows.
*/

WITH staging AS (
    SELECT
        COUNT(*) AS staging_request_count
    FROM {{ ref('stg_311_service_requests') }}
),

mart AS (
    SELECT
        SUM(request_count) AS mart_request_count
    FROM {{ ref('mart_311_agency_performance') }}
)

SELECT
    staging.staging_request_count,
    mart.mart_request_count,
    staging.staging_request_count - mart.mart_request_count AS difference
FROM staging
CROSS JOIN mart
WHERE staging.staging_request_count != mart.mart_request_count