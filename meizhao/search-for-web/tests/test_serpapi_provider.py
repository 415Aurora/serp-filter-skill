from __future__ import annotations

from serp_filter.providers.serpapi import SerpApiProvider


class _FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
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


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, params: dict, timeout: int) -> _FakeResponse:
        self.calls.append((url, params))
        return _FakeResponse()


def test_serpapi_provider_parses_organic_results() -> None:
    session = _FakeSession()
    provider = SerpApiProvider(api_key="secret", session=session)

    results = provider.search(query="best ai directories", limit=10, locale="us")

    assert [result.root_domain for result in results] == ["example.com", "bbc.co.uk"]
    assert results[0].site_name == "Example"
    assert results[1].provider_raw_date == "Mar 1, 2026"
    assert session.calls[0][1]["q"] == "best ai directories"

