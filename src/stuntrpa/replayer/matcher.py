import base64
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from stuntrpa.constants import EPHEMERAL_QUERY_PARAMS


class URLMatcher:
    def __init__(self, ephemeral_params: set[str] | None = None):
        self.ephemeral_params = ephemeral_params or set(EPHEMERAL_QUERY_PARAMS)

    def normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        filtered = {k: v for k, v in params.items() if k.lower() not in {p.lower() for p in self.ephemeral_params}}
        normalized_query = urlencode(filtered, doseq=True)
        return urlunparse(parsed._replace(query=normalized_query))

    def _base_url(self, url: str) -> str:
        parsed = urlparse(url)
        return urlunparse(parsed._replace(query="", fragment=""))

    def find_best_match(
        self,
        har_entries: list[dict],
        url: str,
        method: str,
    ) -> dict | None:
        exact = None
        normalized = None
        base = None

        target_normalized = self.normalize_url(url)
        target_base = self._base_url(url)

        for entry in har_entries:
            req = entry.get("request", {})
            entry_method = req.get("method", "")
            entry_url = req.get("url", "")

            if entry_method != method:
                continue

            if entry_url == url:
                exact = entry
                break

            if normalized is None and self.normalize_url(entry_url) == target_normalized:
                normalized = entry

            if base is None and self._base_url(entry_url) == target_base:
                base = entry

        return exact or normalized or base

    @staticmethod
    def extract_response_body(response: dict) -> bytes | str:
        content = response.get("content", {})
        text = content.get("text", "")
        encoding = content.get("encoding", "")

        if encoding == "base64" and text:
            return base64.b64decode(text)
        return text
