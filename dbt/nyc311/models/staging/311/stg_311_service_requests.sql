WITH source AS (
    SELECT *
    FROM {{ source('nyc311_raw', 'service_requests_2025_01_sample') }}
),

renamed AS (
    SELECT
        unique_key,

        SAFE.PARSE_DATETIME('%Y-%m-%dT%H:%M:%E*S', created_date) AS created_datetime,
        SAFE.PARSE_DATETIME('%Y-%m-%dT%H:%M:%E*S', closed_date) AS closed_datetime,
        SAFE.PARSE_DATETIME('%Y-%m-%dT%H:%M:%E*S', due_date) AS due_datetime,
        SAFE.PARSE_DATETIME('%Y-%m-%dT%H:%M:%E*S', resolution_action_updated_date) AS resolution_action_updated_datetime,

        agency,
        agency_name,
        complaint_type,
        descriptor,
        location_type,
        incident_zip,
        city,
        status,
        resolution_description,
        community_board,
        council_district,
        police_precinct,

        UPPER(TRIM(borough)) AS borough,
        open_data_channel_type,

        SAFE_CAST(latitude AS FLOAT64) AS latitude,
        SAFE_CAST(longitude AS FLOAT64) AS longitude,

        ingested_at,

        closed_date IS NOT NULL AND TRIM(closed_date) != '' AS is_closed,

        latitude IS NOT NULL
            AND longitude IS NOT NULL
            AND SAFE_CAST(latitude AS FLOAT64) BETWEEN 40.4 AND 41.0
            AND SAFE_CAST(longitude AS FLOAT64) BETWEEN -74.3 AND -73.6
            AS has_valid_coordinates

    FROM source
),

final AS (
    SELECT
        *,

        CASE
            WHEN closed_datetime IS NOT NULL
                 AND created_datetime IS NOT NULL
                 AND closed_datetime >= created_datetime
            THEN DATETIME_DIFF(closed_datetime, created_datetime, HOUR) / 24.0
        END AS days_to_close,

        CASE
            WHEN closed_datetime IS NOT NULL
                 AND due_datetime IS NOT NULL
            THEN closed_datetime > due_datetime
        END AS is_late

    FROM renamed
)

SELECT *
FROM final