import argparse
import json
from .client import EventbriteClient
from .config import Settings
from .sync import run_sync

def main():
    parser = argparse.ArgumentParser(description="Resulticks Eventbrite scheduled-pull connector MVP")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("test-connection", help="Check token and list visible organizations")
    sync = sub.add_parser("sync", help="Pull organizations, events, attendees, and orders into normalized JSON files")
    sync.add_argument("--skip-attendees", action="store_true")
    sync.add_argument("--skip-orders", action="store_true")
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.command == "test-connection":
        client = EventbriteClient(settings.token, settings.api_base, settings.timeout_seconds,
                                  settings.max_retries, settings.page_size)
        orgs = client.organizations()
        print(json.dumps({"status":"success","organizations_count":len(orgs),
                          "organizations":[{"id":o.get("id"),"name":o.get("name")} for o in orgs]}, indent=2))
        return
    result = run_sync(settings, fetch_attendees=not args.skip_attendees,
                      fetch_orders=not args.skip_orders)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
