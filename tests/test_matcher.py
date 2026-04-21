import pytest

from stuntrpa.replayer.matcher import URLMatcher


class TestURLMatcherNormalize:
    def test_strips_ephemeral_params(self):
        m = URLMatcher()
        result = m.normalize_url("https://api.example.com/data?_=12345&key=abc")
        assert "_=" not in result
        assert "key=abc" in result

    def test_strips_timestamp(self):
        m = URLMatcher()
        result = m.normalize_url("https://api.example.com/data?timestamp=9999&id=1")
        assert "timestamp=" not in result
        assert "id=1" in result

    def test_preserves_non_ephemeral_params(self):
        m = URLMatcher()
        result = m.normalize_url("https://api.example.com/search?q=test&page=2")
        assert "q=test" in result
        assert "page=2" in result

    def test_case_insensitive_matching(self):
        m = URLMatcher({"Nonce"})
        result = m.normalize_url("https://api.example.com/data?nonce=abc&key=val")
        assert "nonce=" not in result
        assert "key=val" in result

    def test_no_query_params(self):
        m = URLMatcher()
        result = m.normalize_url("https://api.example.com/data")
        assert result == "https://api.example.com/data"


class TestURLMatcherFindBestMatch:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.matcher = URLMatcher()
        self.entries = [
            {
                "request": {"method": "GET", "url": "https://api.example.com/users"},
                "response": {"status": 200, "content": {"text": "users"}},
            },
            {
                "request": {"method": "GET", "url": "https://api.example.com/users?_=12345"},
                "response": {"status": 200, "content": {"text": "users_with_cache"}},
            },
            {
                "request": {"method": "POST", "url": "https://api.example.com/users"},
                "response": {"status": 201, "content": {"text": "created"}},
            },
            {
                "request": {"method": "GET", "url": "https://api.example.com/items?page=1"},
                "response": {"status": 200, "content": {"text": "items"}},
            },
        ]

    def test_exact_match(self):
        result = self.matcher.find_best_match(self.entries, "https://api.example.com/users", "GET")
        assert result is not None
        assert result["response"]["content"]["text"] == "users"

    def test_method_mismatch(self):
        result = self.matcher.find_best_match(self.entries, "https://api.example.com/users", "DELETE")
        assert result is None

    def test_normalized_match_strips_ephemeral(self):
        result = self.matcher.find_best_match(
            self.entries, "https://api.example.com/users?_=99999", "GET"
        )
        assert result is not None

    def test_base_url_fallback(self):
        result = self.matcher.find_best_match(
            self.entries, "https://api.example.com/users?unknown_param=xyz", "GET"
        )
        assert result is not None
        assert result["response"]["content"]["text"] == "users"

    def test_no_match(self):
        result = self.matcher.find_best_match(
            self.entries, "https://api.example.com/nonexistent", "GET"
        )
        assert result is None

    def test_exact_match_takes_priority(self):
        entries = [
            {
                "request": {"method": "GET", "url": "https://api.example.com/data?token=abc&key=1"},
                "response": {"status": 200, "content": {"text": "exact"}},
            },
            {
                "request": {"method": "GET", "url": "https://api.example.com/data?token=xyz&key=2"},
                "response": {"status": 200, "content": {"text": "other"}},
            },
        ]
        result = self.matcher.find_best_match(
            entries, "https://api.example.com/data?token=abc&key=1", "GET"
        )
        assert result["response"]["content"]["text"] == "exact"


class TestExtractResponseBody:
    def test_plain_text(self):
        response = {"content": {"text": "hello world", "encoding": ""}}
        assert URLMatcher.extract_response_body(response) == "hello world"

    def test_base64_encoded(self):
        import base64
        original = b"binary data here"
        encoded = base64.b64encode(original).decode()
        response = {"content": {"text": encoded, "encoding": "base64"}}
        assert URLMatcher.extract_response_body(response) == original

    def test_empty_content(self):
        response = {"content": {}}
        assert URLMatcher.extract_response_body(response) == ""
