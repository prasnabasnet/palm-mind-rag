import re


def normalize_whitespace(text: str) -> str:
    """Collapse all runs of whitespace (including newlines) into single spaces."""
    return re.sub(r"\s+", " ", text).strip()