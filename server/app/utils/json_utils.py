import json
import re
from typing import Any


def extract_json_payload(raw_text: str) -> str:
    """Extract JSON payload from model output, tolerating fenced blocks."""
    text = (raw_text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def parse_json_with_salvage(raw_text: str) -> dict[str, Any]:
    """
    Parse JSON robustly.
    1) Parse as-is.
    2) If failed, salvage first JSON object substring between first '{' and last '}'.
    """
    payload = extract_json_payload(raw_text)
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        start = payload.find("{")
        end = payload.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = payload[start : end + 1]
            candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
            return json.loads(candidate)
        raise
