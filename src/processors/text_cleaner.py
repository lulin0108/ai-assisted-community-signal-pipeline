"""Text cleanup helpers."""

from html.parser import HTMLParser
from html import unescape
import re


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def get_text(self) -> str:
        return " ".join(self.parts)


def clean_text(value: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(value or "")
    text = unescape(parser.get_text())
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def excerpt(value: str, max_chars: int = 240) -> str:
    cleaned = clean_text(value)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."

