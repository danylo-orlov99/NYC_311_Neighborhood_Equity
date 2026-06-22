# Power BI Data Sources

Power BI should connect to dbt mart tables, not raw or staging tables.

## Tables to import

### 1. Daily borough summary

`nyc-311-equity.nyc311_marts.mart_311_daily_borough_summary`

Use for:

- citywide overview
- borough comparison
- daily trends

### 2. Complaint type summary

`nyc-311-equity.nyc311_marts.mart_311_complaint_type_summary`

Use for:

- top complaint types
- issue category comparisons
- closure time by complaint type

### 3. Agency performance

`nyc-311-equity.nyc311_marts.mart_311_agency_performance`

Use for:

- agency volume
- agency closure metrics
- response time comparison

### 4. General complaint summary

`nyc-311-equity.nyc311_marts.mart_311_complaint_summary`

Use for:

- more granular breakdowns by date, hour, borough, agency, complaint type, and status

## Tables not intended for direct dashboard use

### Raw table

`nyc-311-equity.nyc311_raw.service_requests_2025_01`

Reason:

Raw table contains untyped source fields and is not optimized for dashboard use.

### Staging table

`nyc-311-equity.nyc311_staging.stg_311_service_requests`

Reason:

Staging table is useful for modeling and validation but is too row-level for initial dashboard visuals.