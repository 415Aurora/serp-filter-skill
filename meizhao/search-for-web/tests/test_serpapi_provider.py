from __future__ import annotations

from collections import deque

from serp_filter.providers.serpapi import SerpApiProvider


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeSession:
    def __init__(self, payloads: list[dict]) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._payloads = deque(payloads)

    def get(self, url: str, params: dict, timeout: int) -> _FakeResponse:
        self.calls.append((url, params))
        return _FakeResponse(self._payloads.popleft())


def test_serpapi_provider_parses_organic_results() -> None:
    session = _FakeSession(
        [
            {
                "organic_results": [
                    {
                        "position": 1,
                        "title": "Example Tool Directory",
                        "link": "https://www.example.com/tools",
                        "displayed_link": "www.example.com",
                        "source": "Example",
                        "snippet": "A directory of tools",
                    },
                    {
                        "position": 2,
                        "title": "BBC AI Coverage",
                        "link": "https://www.bbc.co.uk/news/technology-1",
                        "displayed_link": "www.bbc.co.uk",
                        "source": "BBC",
                        "snippet": "Latest AI news",
                        "date": "Mar 1, 2026",
                    },
                ]
            }
        ]
    )
    provider = SerpApiProvider(api_key="secret", session=session)

    page = provider.fetch_page(query="best ai directories", page_size=10, locale="us")

    assert [result.root_domain for result in page.results] == ["example.com", "bbc.co.uk"]
    assert page.results[0].site_name == "Example"
    assert page.results[1].provider_raw_date == "Mar 1, 2026"
    assert session.calls[0][1]["q"] == "best ai directories"


def test_serpapi_provider_returns_next_start_when_pagination_available() -> None:
    session = _FakeSession(
        [
            {
                "organic_results": [
                    {
                        "position": 11,
                        "title": "Page 2 Result",
                        "link": "https://www.example.com/page-2",
                        "displayed_link": "www.example.com",
                        "source": "Example",
                        "snippet": "A directory of tools",
                    }
                ],
                "serpapi_pagination": {
                    "next": "https://serpapi.com/search.json?engine=google&q=best+ai+directories&start=10"
                },
            }
        ]
    )
    provider = SerpApiProvider(api_key="secret", session=session)

    page = provider.fetch_page(query="best ai directories", page_size=10, locale="us", start=10)

    assert len(page.results) == 1
    assert page.next_start == 10
    assert session.calls[0][1]["start"] == 10
