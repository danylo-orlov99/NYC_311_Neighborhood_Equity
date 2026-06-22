# Power BI Dashboard Plan

## Project

NYC 311 Neighborhood Equity Monitor

## Dashboard goal

Create an interactive dashboard that summarizes January 2025 NYC 311 service request patterns by borough, complaint type, and responding agency.

The dashboard should help users answer:

1. Which boroughs had the highest 311 request volume?
2. Which complaint types were most common?
3. Which agencies handled the largest share of requests?
4. How did request volume vary over time?
5. Which request types or agencies had slower closure times?
6. Where might further neighborhood-level or equity analysis be useful?

## Current data scope

- Source: NYC Open Data 311 Service Requests from 2020 to Present
- Current extract: January 2025
- Raw table: `nyc-311-equity.nyc311_raw.service_requests_2025_01`
- Staging model: `nyc-311-equity.nyc311_staging.stg_311_service_requests`
- Mart dataset: `nyc-311-equity.nyc311_marts`
- Current row count: 348,180 service requests

## Dashboard pages

### Page 1: Citywide Overview

Purpose:

Give a high-level snapshot of January 2025 311 service request activity.

Primary table:

`nyc-311-equity.nyc311_marts.mart_311_daily_borough_summary`

Suggested visuals:

- KPI card: total requests
- KPI card: closed requests
- KPI card: open requests
- KPI card: median days to close
- Line chart: daily request count
- Bar chart: requests by borough
- Bar chart: median days to close by borough

Suggested slicers:

- Borough
- Date

Metrics:

- `SUM(request_count)`
- `SUM(closed_request_count)`
- `SUM(open_request_count)`
- `AVG(median_days_to_close)`
- `AVG(p90_days_to_close)`
- `AVG(closed_request_share)`

---

### Page 2: Complaint Type Analysis

Purpose:

Identify the most common complaint types and compare closure patterns across issue categories.

Primary table:

`nyc-311-equity.nyc311_marts.mart_311_complaint_type_summary`

Suggested visuals:

- Bar chart: top 15 complaint types by request count
- Bar chart: top complaint types by median days to close
- Bar chart: top complaint types by open request count
- Scatter plot: request count vs median days to close
- Table: complaint type, request count, request share, median days to close, p90 days to close

Suggested slicers:

- Complaint type

Metrics:

- `request_count`
- `request_share`
- `closed_request_count`
- `open_request_count`
- `median_days_to_close`
- `p90_days_to_close`
- `closed_request_share`
- `late_closed_request_share`

---

### Page 3: Agency Performance

Purpose:

Compare responding agencies by request volume, closure rate, and response time.

Primary table:

`nyc-311-equity.nyc311_marts.mart_311_agency_performance`

Suggested visuals:

- Bar chart: requests by agency
- Bar chart: median days to close by agency
- Bar chart: p90 days to close by agency
- Bar chart: closed request share by agency
- Table: agency, agency name, request count, complaint type count, median days to close

Suggested slicers:

- Agency

Metrics:

- `request_count`
- `request_share`
- `closed_request_count`
- `open_request_count`
- `complaint_type_count`
- `median_days_to_close`
- `p90_days_to_close`
- `closed_request_share`
- `late_closed_request_share`

---

### Page 4: Borough Trend Detail

Purpose:

Show how 311 request volume and closure metrics varied by borough over the month.

Primary table:

`nyc-311-equity.nyc311_marts.mart_311_daily_borough_summary`

Suggested visuals:

- Line chart: daily requests by borough
- Line chart: daily median days to close by borough
- Bar chart: total requests by borough
- Matrix: borough by date with request count

Suggested slicers:

- Borough
- Date

Metrics:

- `request_count`
- `closed_request_count`
- `open_request_count`
- `median_days_to_close`
- `p90_days_to_close`
- `closed_request_share`
- `late_closed_request_share`

## Initial dashboard limitations

- Current dashboard uses only January 2025 data.
- Current dashboard does not yet include ACS demographic data.
- Current dashboard does not yet normalize request counts by population.
- Current dashboard does not yet include community district, council district, or ZIP-level equity metrics.
- Current dashboard should describe patterns, not causal effects.

## Future dashboard enhancements

- Add ACS population and demographic denominators.
- Add request rates per 10,000 residents.
- Add community district and council district views.
- Add geospatial mapping.
- Add rolling multi-month trends.
- Add anomaly detection or unusual complaint spikes.
- Add full-year 2025 refresh.