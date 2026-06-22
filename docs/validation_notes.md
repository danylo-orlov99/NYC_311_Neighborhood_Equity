# Raw Data Validation Notes

## Table validated

`nyc-311-equity.nyc311_raw.service_requests_2025_01_sample`

## Load summary

- Source file: nyc-311-equity.nyc311_raw.service_requests_2025_01_sample
- Number of rows in local NDJSON: 5000
- Number of rows loaded to BigQuery: 5000
- Number of distinct unique keys: 5000
- Duplicate unique key rows: 0

## Date coverage

- Minimum created datetime: 2025-01-01T00:00:12
- Maximum created datetime: 2025-01-01T10:59:47
- Notes: Only the first 11 hours of January 1 are covered within these 5000 rows

## Missingness observations

- Missing closed_date: 27
- Missing latitude/longitude: 32
- Missing borough: 0
- Missing community_board: 0
- Missing council_district: 46
- Notes: complaint_type, agency, borough, and created_date are not missing

## Common values

### Top statuses

- 1 Closed      4987 99.74
- 2 In Progress 6    0.12
- 3 Pending     3    0.06
- 4 Assigned    2    0.04
- 5 Open        1    0.02
- 6 Started     1    0.02

### Top boroughs

- 1 BRONX	        2367 47.34
- 2 BROOKLYN	    998	 19.96
- 3 QUEENS	        892	 17.84
- 4 MANHATTAN	    608	 12.16
- 5 STATEN ISLAND	132	2.64
- 6 Unspecified	3	0.06

### Top agencies

- 1	New York City Police Department	4183	83.66
- 2	Department of Housing Preservation and Development	387	7.74
- 3	Department of Transportation	149	2.98
- 4	Department of Sanitation	98	1.96
- 5	Department of Environmental Protection	63	1.26
- 6	Department of Health and Mental Hygiene	32	0.64
- 7	Department of Buildings	25	0.5
- 8	Department of Homeless Services	22	0.44
- 9	Department of Parks and Recreation	18	0.36
- 10	Taxi and Limousine Commission	17	0.34
- 11	Department of Consumer and Worker Protection	3	0.06
- 12	Economic Development Corporation	3	0.06

### Top complaint types

- 1	Noise - Residential	2712	54.24
- 2	Illegal Parking	417	8.34
- 3	Noise - Street/Sidewalk	287	5.74
- 4	HEAT/HOT WATER	216	4.32
- 5	Blocked Driveway	215	4.3
- 6	Noise - Commercial	211	4.22
- 7	Illegal Fireworks	206	4.12
- 8	Street Condition	81	1.62
- 9	Traffic Signal Condition	43	0.86
- 10	UNSANITARY CONDITION	42	0.84

## Data quality flags

- Closed before created: 0
- Due before created: 0
- Unparseable dates: 0
- Coordinates outside rough NYC bounds: 0
- Notes: All looks good

## Decisions for dbt modeling

- Keep raw fields as strings.
- Parse created_date, closed_date, due_date, and resolution_action_updated_date in staging.
- Create a boolean is_closed flag.
- Create a days_to_close metric only when closed_date is present and valid.
- Create a boolean has_valid_coordinates flag.
- Do not filter rows out of the staging model yet unless they are structurally invalid.

## First dbt mart validation

Model: `mart_311_complaint_summary`

Checks performed:

- Confirmed mart row counts reconcile to the 5,000-row staging sample.
- Confirmed `SUM(request_count)` equals 5,000.
- Confirmed created hour coverage matches the raw/staging sample window.
- Created first dashboard-ready summary table grouped by date, hour, borough, agency, complaint type, and status.

Notes:

- This mart is based on a capped 5,000-row sample, not the full January 2025 dataset.
- Early patterns are not representative of the full month because the sample only covers the first ~11 hours of January 1.

## dbt dataset configuration

Configured dbt model outputs by layer:

- Raw source tables are loaded by Python into `nyc311_raw`.
- dbt staging models are built into `nyc311_staging`.
- dbt mart models are built into `nyc311_marts`.

Current dbt objects:

- `nyc-311-equity.nyc311_staging.stg_311_service_requests`
- `nyc-311-equity.nyc311_marts.mart_311_complaint_summary`

Validation:

- Staging model reconciles to 5,000 source rows.
- Mart model reconciles to 5,000 total requests using `SUM(request_count)`.

## Table validated

`nyc-311-equity.nyc311_raw.service_requests_2025_01_full`

## Load summary

- Source file: nyc-311-equity.nyc311_raw.service_requests_2025_01_full
- Number of rows in local NDJSON: 348180
- Number of rows loaded to BigQuery: 348180
- Number of distinct unique keys: 348180
- Duplicate unique key rows: 0
- min_created_date: 2025-01-01T00:00:12.000
- max_created_date: 2025-01-31T23:59:48.000
- rows_missing_closed_date: 2693
- rows_missing_coordinates: 3105

## dbt reconciliation:

- Staging row count: 348180
- Mart `SUM(request_count)`: 348180
- dbt tests passed: yes/no: yes

## Notes:

- This table replaces the earlier 5,000-row sample for modeling.
- The 5,000-row sample was useful for pipeline testing, but all dbt models now point to the full January 2025 raw table.

## Dashboard mart expansion

Created three additional dbt mart models:

- `nyc-311-equity.nyc311_marts.mart_311_daily_borough_summary`
- `nyc-311-equity.nyc311_marts.mart_311_complaint_type_summary`
- `nyc-311-equity.nyc311_marts.mart_311_agency_performance`

Validation:

- `mart_311_daily_borough_summary` reconciles to 348,180 total requests.
- `mart_311_complaint_type_summary` reconciles to 348,180 total requests.
- `mart_311_agency_performance` reconciles to 348,180 total requests.

Purpose:

- Daily borough summary supports time-series and borough comparison visuals.
- Complaint type summary supports top issue and response-time visuals.
- Agency performance summary supports operational performance visuals.

## dbt mart data quality tests

Added custom dbt singular tests to confirm that dashboard marts reconcile to the staging model.

Tests added:

- `assert_daily_borough_summary_reconciles`
- `assert_complaint_type_summary_reconciles`
- `assert_agency_performance_reconciles`
- `assert_no_negative_request_metrics`

Validation logic:

- `SUM(request_count)` in each mart must equal the row count in `stg_311_service_requests`.
- Key request count metrics must not be negative.

Result:

- Full January 2025 staging row count: 348,180
- Daily borough mart reconciles to staging.
- Complaint type mart reconciles to staging.
- Agency performance mart reconciles to staging.
- No negative request metrics found.











