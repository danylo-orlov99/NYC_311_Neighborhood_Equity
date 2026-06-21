/*
Mart: mart_311_complaint_summary

Purpose:
  Create a dashboard-ready summary of NYC 311 service requests.

Grain:
  One row per created_date, created_hour, borough, agency, complaint_type, and status.

Source:
  stg_311_service_requests

Why this matters:
  Power BI should generally connect to clean summary tables rather than raw
  row-level source tables. This model gives us an efficient first dashboard table.
*/

WITH service_requests AS (
    SELECT *
    FROM {{ ref('stg_311_service_requests') }}
),

prepared AS (
    SELECT
        DATE(created_datetime) AS created_date,
        DATETIME_TRUNC(created_datetime, HOUR) AS created_hour,

        borough,
        agency,
        agency_name,
        complaint_type,
        status,

        unique_key,
        is_closed,
        is_late,
        days_to_close,
        has_valid_coordinates

    FROM service_requests
    WHERE created_datetime IS NOT NULL
),

final AS (
    SELECT
        created_date,
        created_hour,
        borough,
        agency,
        agency_name,
        complaint_type,
        status,

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
            SAFE_DIVIDE(COUNTIF(is_closed), COUNT(*)),
            4
        ) AS closed_request_share,

        ROUND(
            SAFE_DIVIDE(COUNTIF(is_late), COUNTIF(is_closed)),
            4
        ) AS late_closed_request_share

    FROM prepared
    GROUP BY
        created_date,
        created_hour,
        borough,
        agency,
        agency_name,
        complaint_type,
        status
)

SELECT *
FROM final