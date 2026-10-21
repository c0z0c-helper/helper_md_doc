"""Preserve literal marker lines without inserting empty HTML paragraphs."""

import re
from typing import List


def _protected_lines(lines: List[str]) -> List[bool]:
    """Identify fenced code, indented code, raw HTML, and display math."""
    protected = []
    closing = None
    for line in lines:
        if closing is not None:
            protected.append(True)
            if re.search(closing, line):
                closing = None
            continue
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        tag = re.match(r"^ {0,3}<(pre|code|script|style|div|table|math)\b", line, re.I)
        if fence:
            marker = fence.group(1)
            closing = rf"^ {{0,3}}{re.escape(marker[0])}{{{len(marker)},}}\s*$"
        elif tag:
            closing = rf"(?i)</{tag.group(1)}>"
        elif line.lstrip().startswith("<!--"):
            closing = r"-->"
        elif line.strip() == "$$":
            closing = r"^\s*\$\$\s*$"
        protected.append(closing is not None or line.startswith(("    ", "\t")))
        if closing and not fence and line.strip() != "$$" and re.search(closing, line):
            closing = None
    return protected


def _literal_marker(line: str) -> bool:
    """Recognize escaped markers and compact labels, excluding emphasis and rules."""
    if re.match(r"^ {0,3}\\[-*]\s+\S", line):
        return True
    return bool(re.match(r"^ {0,3}[-*][^\s\d*\-][^*]*$", line))


def _table_start(lines: List[str], index: int) -> bool:
    """A pipe header row followed by a delimiter row; needs a preceding blank line."""
    if "|" not in lines[index] or index + 1 >= len(lines):
        return False
    return bool(re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$", lines[index + 1])) and "|" in lines[index + 1]


def normalize_spacing(md_text: str) -> str:
    """Separate list blocks and hard-break adjacent literal marker lines only."""
    lines = md_text.lstrip("\ufeff").split("\n")
    protected = _protected_lines(lines)
    result = []
    for index, line in enumerate(lines):
        if protected[index]:
            result.append(line)
            continue
        line = re.sub(r"\\\*\\\*([^*]+?)\\\*\\\*", r"**\1**", line)
        previous = lines[index - 1] if index else ""
        if previous.strip() and not protected[index - 1]:
            if _table_start(lines, index) and "|" not in previous:
                result.append("")
            elif _literal_marker(previous) and _literal_marker(line):
                if not re.search(r"(?: {2,}|<br\s*/?>)\s*$", result[-1]):
                    result[-1] = result[-1].rstrip() + "  "
            elif re.match(r"^ {0,3}(?:[-*+]\s+|\d+\.\s+)", line):
                if not re.match(r"^\s*(?:[-*+]\s+|\d+\.\s+|#)", previous):
                    result.append("")
        result.append(line)
    return "\n".join(result)
