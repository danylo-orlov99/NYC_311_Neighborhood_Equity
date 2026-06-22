/*
Test: assert_no_negative_request_metrics

Purpose:
  Confirm that key mart count metrics are never negative.

Pass condition:
  This query returns zero rows.

Why this matters:
  Counts such as request_count, closed_request_count, open_request_count,
  and late_request_count should never be negative.

Note:
  grain_value is cast to STRING so that the UNION ALL works across marts
  with different grain types, such as DATE, complaint_type, and agency.
*/

SELECT
    'mart_311_daily_borough_summary' AS model_name,
    CAST(created_date AS STRING) AS grain_value,
    request_count,
    closed_request_count,
    open_request_count,
    late_request_count
FROM {{ ref('mart_311_daily_borough_summary') }}
WHERE
    request_count < 0
    OR closed_request_count < 0
    OR open_request_count < 0
    OR late_request_count < 0

UNION ALL

SELECT
    'mart_311_complaint_type_summary' AS model_name,
    CAST(complaint_type AS STRING) AS grain_value,
    request_count,
    closed_request_count,
    open_request_count,
    late_request_count
FROM {{ ref('mart_311_complaint_type_summary') }}
WHERE
    request_count < 0
    OR closed_request_count < 0
    OR open_request_count < 0
    OR late_request_count < 0

UNION ALL

SELECT
    'mart_311_agency_performance' AS model_name,
    agency AS grain_value,
    request_count,
    closed_request_count,
    open_request_count,
    late_request_count
FROM {{ ref('mart_311_agency_performance') }}
WHERE
    request_count < 0
    OR closed_request_count < 0
    OR open_request_count < 0
    OR late_request_count < 0