from serp_filter.domain_utils import normalize_root_domain


def test_normalize_root_domain_collapses_www_and_subdomains() -> None:
    assert normalize_root_domain("https://www.example.com/path") == "example.com"
    assert normalize_root_domain("https://blog.example.com/article") == "example.com"


def test_normalize_root_domain_handles_multilevel_tlds() -> None:
    assert normalize_root_domain("https://subdomain.bbc.co.uk/news") == "bbc.co.uk"
