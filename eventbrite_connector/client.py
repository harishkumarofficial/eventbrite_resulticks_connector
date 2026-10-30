import time
from typing import Any, Iterator
import requests
from requests.exceptions import RequestException

class EventbriteAPIError(RuntimeError):
    pass

class EventbriteClient:
    def __init__(self, token: str, base_url: str, timeout: int = 30, max_retries: int = 5, page_size: int = 50):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.page_size = page_size
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Resulticks-Eventbrite-Connector/0.1",
        })

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    if attempt < self.max_retries:
                        retry_after = response.headers.get("Retry-After")
                        wait = float(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 30)
                        time.sleep(wait)
                        continue
                if not response.ok:
                    raise EventbriteAPIError(
                        f"Eventbrite API returned HTTP {response.status_code} for {path}: {response.text[:1000]}"
                    )
                payload = response.json()
                if not isinstance(payload, dict):
                    raise EventbriteAPIError(f"Expected JSON object from {path}")
                return payload
            except RequestException as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2 ** attempt, 30))
        raise EventbriteAPIError(f"Request failed for {path}: {last_error}")

    def paginated(
        self,
        path: str,
        params: dict[str, Any] | None = None
    ) -> Iterator[dict[str, Any]]:

        base_params = dict(params or {})

        # Never send page_size to the organizations endpoint.
        base_params.pop("page_size", None)

        page = int(base_params.pop("page", 1))

        while True:
            query = dict(base_params)
            query["page"] = page

            print(f"Requesting: {path}, params={query}")

            payload = self.get(path, query)

            list_key = next(
                (
                    key for key, value in payload.items()
                    if isinstance(value, list) and key != "errors"
                ),
                None
            )

            if list_key is None:
                raise EventbriteAPIError(
                    f"No list field found in response for {path}"
                )

            records = payload.get(list_key) or []

            for item in records:
                if isinstance(item, dict):
                    yield item

            pagination = payload.get("pagination") or {}

            page_count = pagination.get("page_count")
            has_more = pagination.get("has_more_items")

            if page_count is not None:
                if page >= int(page_count):
                    break
            elif has_more is not None:
                if not has_more:
                    break
            elif not records:
                break

            page += 1

    def organizations(self) -> list[dict[str, Any]]:
        return list(self.paginated("/users/me/organizations/"))

    def events(self, organization_id: str, statuses: str) -> list[dict[str, Any]]:
        params = {"status": statuses.strip()} if statuses.strip() else {}
        return list(self.paginated(f"/organizations/{organization_id}/events/", params))

    def attendees(self, event_id: str) -> list[dict[str, Any]]:
        return list(self.paginated(f"/events/{event_id}/attendees/"))

    def orders(self, event_id: str):
        return list(
            self.paginated(
                f"/events/{event_id}/orders/"
            )
        )