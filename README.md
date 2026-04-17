# next_train.html Documentation

## Overview
`next_train.html` is a client-side rail departures page that:
- Loads schedule data from `rail_feed.xml` (or another XML path/URL via query param).
- Lets riders choose a stop when no stop is provided.
- Shows next departures for a selected stop.
- Supports direction filtering (northbound, southbound, inbound, outbound, and combo mode).
- Displays station status overlays (closed, delay, alert).
- Displays a bottom scrolling accessibility alert when elevators/escalators are out of service.
- Auto-refreshes every 30 seconds.

This page is fully self-contained (HTML, CSS, JS in one file) and expects companion JSON/XML files in the same folder.

## Required Companion Files
The page expects these relative files by default:
- `rail_feed.xml`
- `rail_dashboard_stations.json`
- `nfta_rail_vertical_assets.json`

If any are missing/unreachable, the UI still attempts to render and falls back safely where possible.

## Runtime Behavior
At startup, the page:
1. Updates the live clock in the header every second.
2. Loads XML feed data.
3. Parses stops, service calendars, calendar exceptions, and trip stop-times.
4. Branches based on URL query params:
   - No `stop`: shows a searchable stop picker.
   - With `stop`: resolves stop, applies station status rules, and renders departures (or alert states).
5. Re-runs full load/render every 30 seconds.

## Query Parameters
- `stop`
  - Stop selector. Matches by `stop_id` or `stop_code` (case-insensitive fallback checks included).
  - If omitted, stop picker view is shown.

- `dir`
  - Direction filter. Accepted values:
    - `all`, `any`, `both`, `*`
    - `north`, `northbound`, `n`, `nb`
    - `south`, `southbound`, `s`, `sb`
    - `inbound`, `in`, `ib`
    - `outbound`, `out`, `ob`
    - `combo`, `combined`
    - `0` (maps to `direction_id=0`)
    - `1` (maps to `direction_id=1`)
  - If omitted on stop-picker route, the page defaults the URL to `dir=combo`.

- `xml`
  - Optional XML path/URL override.
  - Default: `rail_feed.xml`.

- `max`
  - Optional number of upcoming trains to display.
  - If blank, missing, invalid, or <= 0, defaults to `2`.

- `adamsg`
  - Optional ADA message toggle.
  - Use `adamsg=true` (or `1`, `yes`, `on`) to show a red ADA banner after the departure rows.
  - Banner text: `ADA ALERT & SEE DETAILS`.

## Direction Mapping
Feed direction IDs are interpreted as:
- `1` => northbound
- `0` => southbound

Inbound/outbound filtering is used in stop-picker mode via station metadata from `rail_dashboard_stations.json`.

## Data Parsing
From `rail_feed.xml`, the page parses:
- Stops (`stops > stop`)
- Weekly service calendar (`services > calendar > service`)
- Calendar exceptions (`services > calendar_dates > service > date`)
- Trips and stop times (`trips > trip > stop_times > stop_time`)

Service activation for "today" is computed using:
- Weekly calendar day flags + start/end dates
- Calendar date exception adds/removes

## Departure Selection Rules
For a selected stop:
- Ignore trips not active today.
- Apply direction filter.
- Keep only departures at/after current local time.
- Sort ascending by departure time.
- Show up to `max` trains (defaults to 2).

Combo mode:
- Finds both platform stops that share the same normalized station name.
- Builds separate northbound/southbound lists.
- Takes up to `max` per direction, merges, sorts, and caps at `max * 2`.

## Station Status and Alert Priority
Station status data comes from `rail_dashboard_stations.json` (`stations` array).

Per selected stop, matching rows are identified by stop code/ID fields. Priority is:
1. `CLOSED`
2. `ALERT`
3. `DELAY`
4. `OPEN`

Rendering behavior:
- `CLOSED`: full-screen "STATION CLOSED" banner.
- `DELAY` or `ALERT`: full-screen alert card with title/message/detail.
- `OPEN`: normal departure list view.

## Accessibility Asset Alert (Bottom Ticker)
From `nfta_rail_vertical_assets.json` (`assets` array):
- Filters to elevator/escalator asset types.
- Filters to out-of-service statuses (`OFF`, `DOWN`, `OUT OF SERVICE`, `OOS`, etc.).
- Matches assets to current station by name, station number/code, or GTFS stop ID.
- If matches exist, shows a fixed bottom scrolling warning line.

## Refresh and Time
- Clock update: every 1 second.
- Data reload/render: every 30 seconds (`REFRESH_MS = 30000`).

## Error Handling
- Global `window.onerror` writes a visible error message in the content area.
- XML fetch and parse failures show a detailed error panel.
- If opened as `file://`, a hint is shown recommending a local web server.

## UI States
Major UI states include:
- Loading
- Stop picker
- Normal departures
- No service today
- No departures today
- After-hours
- Stop not found
- Station closed
- Delay/alert screen
- Runtime error

## Local Usage
Open with a local server from this folder (recommended):

PowerShell example:

```powershell
python -m http.server 8000
```

Then browse:
- `http://localhost:8000/next_train.html`

Example with stop and direction:
- `http://localhost:8000/next_train.html?stop=11440&dir=north`

Example with stop, direction, and custom count:
- `http://localhost:8000/next_train.html?stop=11440&dir=north&max=3`

Example with ADA banner enabled:
- `http://localhost:8000/next_train.html?stop=11440&dir=north&max=3&adamsg=true`

## Tunable Constants
Inside the script:
- `REFRESH_MS` (default `30000`)
- `DEFAULT_MAX_TRAINS` (default `2`)
- `DEFAULT_XML_URL`
- `STATION_STATUS_JSON_URL`
- `VERTICAL_ASSETS_JSON_URL`

## Notes for Maintenance
- The file contains repeated local `escapeHtml` helpers in multiple scopes; behavior is consistent but could be centralized.
- In combo mode, section headers (`directionHeader`) are styled in CSS but currently not rendered in markup.
- The stop-picker "Inbound/Outbound" logic depends on station JSON `platform_direction` quality.

