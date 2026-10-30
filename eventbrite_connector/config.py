from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}

@dataclass(frozen=True)
class Settings:
    token: str
    api_base: str = "https://www.eventbriteapi.com/v3"
    output_dir: str = "eventbrite_json"
    page_size: int = 50
    timeout_seconds: int = 30
    max_retries: int = 5
    event_statuses: str = "draft,live,started,ended,completed,canceled"
    fetch_attendees: bool = True
    fetch_orders: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("EVENTBRITE_PRIVATE_TOKEN", "").strip()
        if not token:
            raise ValueError("EVENTBRITE_PRIVATE_TOKEN is missing. Set it in your environment or .env file.")
        return cls(
            token=token,
            api_base=os.getenv("EVENTBRITE_API_BASE", "https://www.eventbriteapi.com/v3").rstrip("/"),
            output_dir=os.getenv("EVENTBRITE_OUTPUT_DIR", "eventbrite_json"),
            page_size=max(1, min(int(os.getenv("EVENTBRITE_PAGE_SIZE", "50")), 100)),
            timeout_seconds=int(os.getenv("EVENTBRITE_TIMEOUT_SECONDS", "30")),
            max_retries=max(0, int(os.getenv("EVENTBRITE_MAX_RETRIES", "5"))),
            event_statuses=os.getenv("EVENTBRITE_EVENT_STATUSES", "draft,live,started,ended,completed,canceled"),
            fetch_attendees=_bool("EVENTBRITE_FETCH_ATTENDEES", True),
            fetch_orders=_bool("EVENTBRITE_FETCH_ORDERS", True),
        )
