# Resulticks Eventbrite Connector (JSON MVP)

A standalone Python reference connector inspired by the inbound Aura ETL pattern in the Resulticks Marketo integration BRD. This version **does not use a database**. It fetches Eventbrite records and writes JSON files for each entity plus individual and grouped relationships.

## What it extracts

- Organizations visible to the authenticated Eventbrite account
- Events returned by the organization events endpoint, requesting draft/live/started/ended/completed/canceled statuses
- Attendees and orders per event (configurable)
- Normalized people, using lower-cased/trimmed email as the MVP identity key when email is present
- Person-to-event relationship records and one grouped record per person

## Setup

1. Rotate/revoke credentials pasted into chat, source code, or logs. Never commit credentials.
2. Use Python 3.10+ and install dependencies:

   ```bash
   python -m venv .venv
   # Windows PowerShell: .\.venv\Scripts\Activate.ps1
   # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set a newly rotated `EVENTBRITE_PRIVATE_TOKEN` locally.
4. Test authentication and organization access:

   ```bash
   python -m eventbrite_connector.cli test-connection
   ```
5. Run the pull:

   ```bash
   python -m eventbrite_connector.cli sync
   ```
6. Optional flags:

   ```bash
   python -m eventbrite_connector.cli sync --skip-attendees
   python -m eventbrite_connector.cli sync --skip-orders
   ```

## JSON output structure

The default output folder is `eventbrite_json/` (configurable with `EVENTBRITE_OUTPUT_DIR`). Each run replaces the current snapshot files.

```text
eventbrite_json/
├── organizations.json
├── events.json
├── people.json
├── attendees.json
├── orders.json
├── sync_summary.json
└── relationships/
    ├── person_events.json
    └── grouped_people_events.json
```

- `organizations.json`: source organization records.
- `events.json`: source event fields plus `organization_id` and flattened `event_name`.
- `people.json`: one normalized person per email. Records without email remain in their attendee/order entity file but are not merged into `people.json`.
- `attendees.json` and `orders.json`: source records plus `organization_id` and `event_id`.
- `relationships/person_events.json`: one relationship per person/event pair with registration/order counts, check-in/cancellation/refund indicators and activity timestamps.
- `relationships/grouped_people_events.json`: one record per person with `event_count`, `event_ids`, nested `events`, `registration_count`, `order_count`, and `checked_in_event_count`.
- `sync_summary.json`: record counts, output folder, status and generation time.

### Example grouped relationship

```json
{
  "person_id": "email:person@example.com",
  "email": "person@example.com",
  "full_name": "Example Person",
  "event_count": 2,
  "event_ids": ["event-101", "event-205"],
  "events": [
    {"event_id": "event-101", "event_name": "Product Launch", "has_registration": true, "has_order": true},
    {"event_id": "event-205", "event_name": "Customer Meetup", "has_registration": true, "has_order": true}
  ]
}
```

The example is illustrative, not live Eventbrite data. Actual nested event relationship entries include additional count and status fields.

## API endpoints

- `GET /v3/users/me/organizations/`
- `GET /v3/organizations/{organization_id}/events/`
- `GET /v3/events/{event_id}/attendees/`
- `GET /v3/events/{event_id}/orders/`

Pagination and retry handling are implemented in the client. No writes are made back to Eventbrite. No live API calls were performed while packaging this code; run `test-connection` locally to validate your token and permissions.

## Scope and caveats

This is a JSON snapshot/reference connector, not an approved Aura plugin or production destination adapter. It currently performs full pulls and overwrites the JSON snapshot files. It does not implement incremental watermarks, webhook ingestion, deleted-record reconciliation, or a final Resulticks/Aura ingestion contract. Draft-event visibility depends on what Eventbrite returns for the authenticated account and endpoint filters. Identity resolution by email is an MVP assumption and should be aligned with Resulticks CDP identity rules before production use.
