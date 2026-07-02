/*
Mart: mart_311_daily_geography_complaint_summary

Purpose:
  Summarize NYC 311 service requests by date, geography, agency, and complaint type.

Grain:
  One row per created_date, borough, council_district, community_board,
  agency, and complaint_type.

Dashboard use:
  - Geography Explorer page
  - Trend Explorer page
  - Summary & Rankings page
  - complaint type visuals filtered by date and geography
*/

WITH service_requests AS (
    SELECT *
    FROM {{ ref('stg_311_service_requests') }}
    WHERE created_datetime IS NOT NULL
),

prepared AS (
    SELECT
        DATE(created_datetime) AS created_date,

        COALESCE(NULLIF(TRIM(borough), ''), 'UNKNOWN') AS borough,
        COALESCE(NULLIF(TRIM(council_district), ''), 'UNKNOWN') AS council_district,
        COALESCE(NULLIF(TRIM(community_board), ''), 'UNKNOWN') AS community_board,

        COALESCE(NULLIF(TRIM(agency), ''), 'UNKNOWN') AS agency,
        COALESCE(NULLIF(TRIM(agency_name), ''), 'UNKNOWN') AS agency_name,
        COALESCE(NULLIF(TRIM(complaint_type), ''), 'UNKNOWN') AS complaint_type,

        unique_key,
        is_closed,
        is_late,
        days_to_close,
        has_valid_coordinates

    FROM service_requests
),

final AS (
    SELECT
        created_date,
        borough,
        council_district,
        community_board,
        agency,
        agency_name,
        complaint_type,

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

    FROM prepared
    GROUP BY
        created_date,
        borough,
        council_district,
        community_board,
        agency,
        agency_name,
        complaint_type
)

SELECT *
FROM final