from __future__ import annotations

from serp_filter.domain_dates import RdapDomainDateLookup


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class _FakeSession:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.requested_urls: list[str] = []

    def get(self, url: str, timeout: int) -> _FakeResponse:
        self.requested_urls.append(url)
        return _FakeResponse(self.payload)


def test_rdap_lookup_extracts_created_date() -> None:
    session = _FakeSession(
        {
            "events": [
                {"eventAction": "last changed", "eventDate": "2024-01-01T00:00:00Z"},
                {"eventAction": "registration", "eventDate": "1998-07-15T04:00:00Z"},
            ]
        }
    )
    lookup = RdapDomainDateLookup(session=session)

    created_at, source = lookup("bbc.co.uk")

    assert created_at == "1998-07-15"
    assert source == "rdap"
    assert session.requested_urls == ["https://rdap.org/domain/bbc.co.uk"]


def test_rdap_lookup_returns_unknown_when_no_registration_event() -> None:
    session = _FakeSession({"events": []})
    lookup = RdapDomainDateLookup(session=session)

    created_at, source = lookup("example.com")

    assert created_at is None
    assert source == "rdap_missing"

