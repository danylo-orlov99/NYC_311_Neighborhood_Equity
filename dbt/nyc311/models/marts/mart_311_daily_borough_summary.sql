/*
Mart: mart_311_daily_borough_summary

Purpose:
  Summarize NYC 311 service requests by day and borough.

Grain:
  One row per created_date and borough.

Dashboard use:
  - daily request trends
  - borough comparison
  - closure rate
  - late closure rate
  - median response time
*/

WITH service_requests AS (
    SELECT *
    FROM {{ ref('stg_311_service_requests') }}
    WHERE created_datetime IS NOT NULL
),

daily_borough AS (
    SELECT
        DATE(created_datetime) AS created_date,
        borough,

        COUNT(*) AS request_count,
        COUNTIF(is_closed) AS closed_request_count,
        COUNTIF(NOT is_closed) AS open_request_count,
        COUNTIF(is_late) AS late_request_count,
        COUNTIF(has_valid_coordinates) AS valid_coordinate_count,

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
            SAFE_DIVIDE(COUNTIF(is_closed), COUNT(*)),
            4
        ) AS closed_request_share,

        ROUND(
            SAFE_DIVIDE(COUNTIF(is_late), COUNTIF(is_closed)),
            4
        ) AS late_closed_request_share

    FROM service_requests
    GROUP BY
        created_date,
        borough
)

SELECT *
FROM daily_borough