"""Tests for centuria.utils module."""

import pytest

from centuria.utils import extract_json_from_text, parse_json_response


class TestParseJsonResponse:
    def test_plain_json(self):
        result = parse_json_response('{"name": "Alice", "age": 30}')
        assert result == {"name": "Alice", "age": 30}

    def test_json_with_markdown_block(self):
        content = """```json
{"name": "Bob", "age": 25}
```"""
        result = parse_json_response(content)
        assert result == {"name": "Bob", "age": 25}

    def test_json_with_plain_code_block(self):
        content = """```
{"name": "Carol", "age": 35}
```"""
        result = parse_json_response(content)
        assert result == {"name": "Carol", "age": 35}

    def test_json_with_whitespace(self):
        content = """

  {"name": "Dave", "age": 40}

"""
        result = parse_json_response(content)
        assert result == {"name": "Dave", "age": 40}

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):
            parse_json_response("not json at all")


class TestExtractJsonFromText:
    def test_plain_json(self):
        result = extract_json_from_text('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_markdown(self):
        result = extract_json_from_text('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        text = """Here is the response:
{"name": "Test"}
That's the data."""
        result = extract_json_from_text(text)
        assert result == {"name": "Test"}

    def test_no_json_returns_none(self):
        result = extract_json_from_text("Just some plain text here")
        assert result is None
