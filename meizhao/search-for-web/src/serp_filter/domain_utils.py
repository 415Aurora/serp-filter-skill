from __future__ import annotations

from urllib.parse import urlparse

import tldextract


EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=None)


def normalize_root_domain(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        return ""

    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    host = parsed.netloc or parsed.path
    extracted = EXTRACTOR(host)
    if not extracted.domain or not extracted.suffix:
        return host.lower().strip(".")
    return f"{extracted.domain}.{extracted.suffix}".lower()
