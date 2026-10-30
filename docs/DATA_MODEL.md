# Proposed Eventbrite-to-Resulticks data model

This follows the Marketo BRD's inbound extraction pattern and its distinction between individual/person data, source records, relationship data, and derived behavioral attributes.

| Entity | Grain/key | Relationship | Use |
|---|---|---|---|
| Organization | `organization_id` | Connected account | Source account scope |
| Event | `event_id` | `organization_id` | Event attributes/status/schedule |
| Attendee | `attendee_id` | `event_id`, `organization_id` | Registration, ticket, check-in/cancel/refund |
| Order | `order_id` | `event_id`, `organization_id` | Transaction/purchaser association |
| Person | Normalized email where present | Derived from attendee/order profile | Unified audience profile |
| Person-event | One row per `person_id` + `event_id` | Person and event | Which events a person registered/ordered for |

## Individual data

Person: normalized email identity key and names; raw source data remains available in attendee/order JSON files.
Event: event/organization IDs, name, status, start/end UTC, currency, URL, raw JSON.
Attendee: attendee/event/order IDs, person ID, ticket class, status, check-in/cancel/refund flags, timestamps, raw JSON.
Order: order/event IDs, person ID, status, timestamps, gross amount/currency when supplied, raw JSON.

## Grouped/derived data

`person_events` retains registration/order flags and counts, check-in/cancel/refund flags, and first/last activity timestamps.
`relationships/grouped_people_events.json` contains one grouped record per person, with event count, event IDs, nested event relationship summaries, registration/order counts, and checked-in-event count. JSON files are snapshots rather than database tables or views.

Potential segments:
- registered for at least two webinars
- registered but did not check in
- checked in at a previous event
- purchased a ticket for a specific event
- cancelled/refunded registrations excluded from selected journeys

Do not infer marketing consent from event registration. Campaign eligibility must honor consent, channel permissions, suppression rules, and privacy requirements.

## Identity caveat

Email is only an MVP matching key (trimmed and case-folded), not a guaranteed universal customer ID. Records without email remain in source attendee/order tables and are not merged into a person profile. Production identity resolution must follow Resulticks CDP rules.

## Draft events

The event request includes draft in a configurable status filter. The connector persists a draft if the API returns it. Verify draft visibility against the test account/token; permissions and Eventbrite API behavior may affect access.
