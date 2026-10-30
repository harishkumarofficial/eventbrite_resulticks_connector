# Alignment with Resulticks Marketo Integration BRD

The Marketo BRD describes an inbound Aura ETL connector with scheduled/on-demand extraction, pagination, retries, transformation/mapping, identity resolution, loading, monitoring, and derived behavioral attributes. Outbound writes are out of scope for the initial release.

| Marketo BRD concept | Eventbrite MVP equivalent |
|---|---|
| Lead/person | `people`, derived from attendee/order profiles |
| Activity/list/program membership | Attendee/order records plus `person_events` relationships |
| Account/program hierarchy | Organization -> event |
| Scheduled inbound pull | `python -m eventbrite_connector.cli sync` |
| Field mapping | Normalized columns plus raw JSON |
| Deduplication | Email-normalized person key (MVP only) |
| Monitoring | `sync_summary.json` with status/counts |
| Outbound excluded | No Eventbrite writes, event creation, publishing, or webhook support |

## Production gaps
1. Map the JSON entities and relationships into the approved Aura/Resulticks ingestion contract.
2. Confirm source fields and mappings with Product/Data/CDP.
3. Verify API access and draft-event visibility.
4. Implement incremental checkpoints only after validating endpoint filters and Aura checkpoint strategy.
5. Define deletion/unpublish and reconciliation behavior.
6. Integrate secrets management and structured logs/metrics.
7. Review PII security/retention.
8. QA auth failures, rate limits, pagination, duplicates, and partial failures.
