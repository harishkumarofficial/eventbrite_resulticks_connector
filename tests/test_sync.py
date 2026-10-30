import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from eventbrite_connector.config import Settings
from eventbrite_connector.sync import run_sync


class FakeClient:
    def __init__(self, *args, **kwargs):
        pass
    def organizations(self):
        return [{"id": "org1", "name": "Demo Org"}]
    def events(self, org_id, statuses):
        return [
            {"id": "event1", "name": {"text": "Event One"}, "status": "draft"},
            {"id": "event2", "name": {"text": "Event Two"}, "status": "live"},
        ]
    def attendees(self, event_id):
        return [{"id": f"att-{event_id}", "profile": {"email": "Test@Example.com", "first_name": "Test"}, "checked_in": event_id == "event2"}]
    def orders(self, event_id):
        return [{"id": f"order-{event_id}", "email": "test@example.com", "status": "placed"}]


def test_sync_writes_entity_and_grouped_relationship_json():
    with TemporaryDirectory() as tmp:
        settings = Settings(token="fake", output_dir=tmp)
        with patch("eventbrite_connector.sync.EventbriteClient", FakeClient):
            result = run_sync(settings)
        assert result["status"] == "success"
        assert result["events"] == 2
        people = json.loads((Path(tmp) / "people.json").read_text())
        grouped = json.loads((Path(tmp) / "relationships" / "grouped_people_events.json").read_text())
        rels = json.loads((Path(tmp) / "relationships" / "person_events.json").read_text())
        assert len(people) == 1
        assert len(grouped) == 1
        assert grouped[0]["event_count"] == 2
        assert len(grouped[0]["events"]) == 2
        assert len(rels) == 2
        assert grouped[0]["email"] == "test@example.com"
