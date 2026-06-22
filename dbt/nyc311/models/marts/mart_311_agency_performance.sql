/*
Mart: mart_311_agency_performance

Purpose:
  Summarize request volume and closure metrics by responding agency.

Grain:
  One row per agency and agency_name.

Dashboard use:
  - agency request volume
  - agency closure rate
  - agency late closure rate
  - agency response time
*/

WITH service_requests AS (
    SELECT *
    FROM {{ ref('stg_311_service_requests') }}
    WHERE created_datetime IS NOT NULL
),

agency_summary AS (
    SELECT
        agency,
        agency_name,

        COUNT(*) AS request_count,
        COUNTIF(is_closed) AS closed_request_count,
        COUNTIF(NOT is_closed) AS open_request_count,
        COUNTIF(is_late) AS late_request_count,
        COUNTIF(has_valid_coordinates) AS valid_coordinate_count,

        COUNT(DISTINCT complaint_type) AS complaint_type_count,
        COUNT(DISTINCT borough) AS borough_count,

        ROUND(AVG(days_to_close), 2) AS avg_days_to_close,

        ROUND(
            APPROX_QUANTILES(days_to_close, 100 IGNORE NULLS)[OFFSET(50)],
            2
        ) AS median_days_to_close,

        ROUND(
            APPROX_QUANTILES(days_to_close, 100 IGNORE NULLS)[OFFSET(90)],
            2
        ) AS p90_days_to_close,

        ROUND(
            SAFE_DIVIDE(COUNT(*), SUM(COUNT(*)) OVER ()),
            4
        ) AS request_share,

        ROUND(
            SAFE_DIVIDE(COUNTIF(is_closed), COUNT(*)),
            4
        ) AS closed_request_share,

        ROUND(
            SAFE_DIVIDE(COUNTIF(is_late), COUNTIF(is_closed)),
            4
        ) AS late_closed_request_share

    FROM service_requests
    GROUP BY
        agency,
        agency_name
)

SELECT *
FROM agency_summary