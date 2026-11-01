"""Conservative URL extraction and normalization shared by NLP stages."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit


URL_TOKEN = re.compile(
    r"(?<![@\w])((?:https?://|www\.)[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+)",
    re.IGNORECASE,
)


def canonicalize_url(value: str) -> str:
    """Return one conservative absolute ASCII HTTP(S) URL from source text.

    Adjacent Indic text is not a valid ASCII URL component and is deliberately
    excluded. Unicode host names remain out of scope until an explicit IDNA
    policy is introduced.
    """
    match = URL_TOKEN.search(value.strip())
    if match is None:
        raise ValueError("value does not contain a supported HTTP(S) URL")
    token = match.group(1).rstrip(".,;:!?)]}")
    if token.casefold().startswith("www."):
        token = f"https://{token}"
    parsed = urlsplit(token)
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must contain an HTTP(S) scheme and host")
    return urlunsplit(
        (parsed.scheme.casefold(), parsed.netloc.casefold(), parsed.path, parsed.query, parsed.fragment)
    )
