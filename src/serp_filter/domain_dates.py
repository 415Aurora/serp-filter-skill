from __future__ import annotations

from dataclasses import dataclass
from time import sleep

import requests


@dataclass(slots=True)
class RdapDomainDateLookup:
    session: requests.Session | object | None = None
    base_url: str = "https://rdap.org/domain"
    min_interval_seconds: float = 0.0

    def __call__(self, domain: str) -> tuple[str | None, str]:
        if self.min_interval_seconds > 0:
            sleep(self.min_interval_seconds)
        client = self.session or requests.Session()
        response = client.get(f"{self.base_url}/{domain}", timeout=30)
        response.raise_for_status()
        payload = response.json()
        for event in payload.get("events", []):
            if event.get("eventAction") == "registration" and event.get("eventDate"):
                return str(event["eventDate"])[:10], "rdap"
        return None, "rdap_missing"

