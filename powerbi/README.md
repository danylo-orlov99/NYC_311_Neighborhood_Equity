# Power BI Dashboard

This folder contains Power BI dashboard assets for the NYC 311 Neighborhood Equity Monitor.

## Current report

`nyc_311_neighborhood_equity.pbix`

## Data source

Power BI connects to BigQuery mart tables created by dbt:

- `nyc-311-equity.nyc311_marts.mart_311_daily_borough_summary`
- `nyc-311-equity.nyc311_marts.mart_311_complaint_type_summary`
- `nyc-311-equity.nyc311_marts.mart_311_agency_performance`

## Current dashboard page

### Citywide Overview

Includes:

- Total requests
- Closed requests
- Open requests
- Closure rate
- Daily request trend by borough
- Request volume by borough
- Median days to close by borough

## Notes

The current dashboard uses January 2025 NYC 311 service requests only.

### Complaint Type Analysis

Includes:

- Total requests by complaint type
- Closed and open request counts
- Top complaint types by volume
- Complaint types with longer median closure times
- Open requests by complaint type
- Complaint type detail table

### Agency Performance

Includes:

- Request volume by responding agency
- Closed and open request counts by agency
- Median days to close by agency
- 90th percentile days to close by agency
- Agency detail table with request share and closure metrics

Interpretation note:

Agency-level response metrics are descriptive and should not be interpreted as causal performance comparisons because agencies handle different types of service requests.

### Borough Trend Detail

Includes:

- Daily 311 request trends by borough
- Daily median days to close by borough
- Total requests by borough
- Daily request count matrix
- Borough and date range slicers

Interpretation note:

Borough-level comparisons are descriptive and are not population-adjusted. Future versions should add ACS population denominators and request rates per 10,000 residents.