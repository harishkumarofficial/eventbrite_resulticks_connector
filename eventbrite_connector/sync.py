"""Pull Eventbrite data and write normalized JSON entity files and relationships."""
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .client import EventbriteClient
from .config import Settings


def _email(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().casefold()


def _name(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("text") or value.get("html")
    return value if isinstance(value, str) else None


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def run_sync(settings: Settings, *, fetch_attendees: bool | None = None, fetch_orders: bool | None = None) -> dict[str, Any]:
    want_attendees = settings.fetch_attendees if fetch_attendees is None else fetch_attendees
    want_orders = settings.fetch_orders if fetch_orders is None else fetch_orders
    client = EventbriteClient(settings.token, settings.api_base, settings.timeout_seconds,
                              settings.max_retries, settings.page_size)
    output_dir = Path(settings.output_dir)
    organizations: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    attendees: list[dict[str, Any]] = []
    orders: list[dict[str, Any]] = []
    people: dict[str, dict[str, Any]] = {}
    relationships: dict[tuple[str, str], dict[str, Any]] = {}
    counts = {"organizations": 0, "events": 0, "attendees": 0, "orders": 0}

    def upsert_person(profile: dict[str, Any], raw: dict[str, Any]) -> str | None:
        email = _email(profile.get("email"))
        if not email:
            return None
        person_id = f"email:{email}"
        first = profile.get("first_name")
        last = profile.get("last_name")
        full_name = profile.get("name") or " ".join(part for part in (first, last) if part) or None
        person = people.setdefault(person_id, {
            "person_id": person_id, "email": email, "first_name": first,
            "last_name": last, "full_name": full_name, "source": "eventbrite"
        })
        for key, value in (("first_name", first), ("last_name", last), ("full_name", full_name)):
            if value and not person.get(key):
                person[key] = value
        return person_id

    def add_relationship(person_id: str | None, org_id: str, event_id: str,
                         *, attendee: dict[str, Any] | None = None, order: dict[str, Any] | None = None) -> None:
        if not person_id:
            return
        key = (person_id, event_id)
        rel = relationships.setdefault(key, {
            "person_id": person_id, "organization_id": org_id, "event_id": event_id,
            "has_registration": False, "has_order": False, "attendee_count": 0,
            "order_count": 0, "checked_in": False, "cancelled": False,
            "refunded": False, "activity_timestamps": []
        })
        if attendee is not None:
            rel["has_registration"] = True
            rel["attendee_count"] += 1
            rel["checked_in"] = rel["checked_in"] or bool(attendee.get("checked_in"))
            rel["cancelled"] = rel["cancelled"] or bool(attendee.get("cancelled"))
            rel["refunded"] = rel["refunded"] or bool(attendee.get("refunded"))
            rel["activity_timestamps"].extend(v for v in (attendee.get("created"), attendee.get("changed")) if v)
        if order is not None:
            rel["has_order"] = True
            rel["order_count"] += 1
            rel["cancelled"] = rel["cancelled"] or str(order.get("status", "")).lower() in {"canceled", "cancelled"}
            rel["activity_timestamps"].extend(v for v in (order.get("created"), order.get("changed")) if v)

    try:
        for org in client.organizations():
            org_id = str(org.get("id") or "")
            if not org_id:
                continue
            organizations.append(org)
            counts["organizations"] += 1
            for raw_event in client.events(org_id, settings.event_statuses):
                event_id = str(raw_event.get("id") or "")
                if not event_id:
                    continue
                event = dict(raw_event)
                event["organization_id"] = org_id
                event["event_name"] = _name(raw_event.get("name"))
                events.append(event)
                counts["events"] += 1
                if want_attendees:
                    for raw_attendee in client.attendees(event_id):
                        attendee = dict(raw_attendee)
                        attendee["organization_id"] = org_id
                        attendee["event_id"] = event_id
                        attendees.append(attendee)
                        counts["attendees"] += 1
                        profile = raw_attendee.get("profile") or {}
                        person_id = upsert_person(profile, raw_attendee)
                        add_relationship(person_id, org_id, event_id, attendee=raw_attendee)
                if want_orders:
                    for raw_order in client.orders(event_id):
                        order = dict(raw_order)
                        order["organization_id"] = org_id
                        order["event_id"] = event_id
                        orders.append(order)
                        counts["orders"] += 1
                        profile = {"email": raw_order.get("email"), "first_name": raw_order.get("first_name"),
                                   "last_name": raw_order.get("last_name"), "name": raw_order.get("name")}
                        person_id = upsert_person(profile, raw_order)
                        add_relationship(person_id, org_id, event_id, order=raw_order)

        person_events = []
        grouped: dict[str, dict[str, Any]] = {}
        event_names = {str(e.get("id")): e.get("event_name") for e in events}
        for rel in relationships.values():
            timestamps = sorted(rel.pop("activity_timestamps"))
            rel["first_activity_at"] = timestamps[0] if timestamps else None
            rel["last_activity_at"] = timestamps[-1] if timestamps else None
            rel["event_name"] = event_names.get(rel["event_id"])
            person_events.append(rel)
            person_id = rel["person_id"]
            group = grouped.setdefault(person_id, {
                **people[person_id], "event_count": 0, "event_ids": [], "events": [],
                "registration_count": 0, "order_count": 0, "checked_in_event_count": 0
            })
            group["event_count"] += 1
            group["event_ids"].append(rel["event_id"])
            group["events"].append({"event_id": rel["event_id"], "event_name": rel["event_name"],
                                    "has_registration": rel["has_registration"], "has_order": rel["has_order"],
                                    "attendee_count": rel["attendee_count"], "order_count": rel["order_count"],
                                    "checked_in": rel["checked_in"], "cancelled": rel["cancelled"], "refunded": rel["refunded"]})
            group["registration_count"] += rel["attendee_count"]
            group["order_count"] += rel["order_count"]
            group["checked_in_event_count"] += int(rel["checked_in"])

        _write_json(output_dir / "organizations.json", organizations)
        _write_json(output_dir / "events.json", events)
        _write_json(output_dir / "people.json", list(people.values()))
        _write_json(output_dir / "attendees.json", attendees)
        _write_json(output_dir / "orders.json", orders)
        _write_json(output_dir / "relationships" / "person_events.json", person_events)
        _write_json(output_dir / "relationships" / "grouped_people_events.json", list(grouped.values()))
        result = {"status": "success", **counts, "people": len(people),
                  "person_event_relationships": len(person_events), "output_dir": str(output_dir.resolve()),
                  "generated_at": datetime.now(timezone.utc).isoformat()}
        _write_json(output_dir / "sync_summary.json", result)
        return result
    except Exception as exc:
        failure = {"status": "failed", **counts, "error": str(exc)[:2000],
                   "generated_at": datetime.now(timezone.utc).isoformat()}
        _write_json(output_dir / "sync_summary.json", failure)
        raise
