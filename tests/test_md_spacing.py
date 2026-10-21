"""Regression coverage for Markdown list structure and DOCX line breaks."""

from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest

from helper_md_doc import md_to_doc, md_to_html
from helper_md_doc.helper_md_html import normalize_markdown_spacing


@pytest.mark.parametrize("marker", ["- ", "* ", "+ "])
@pytest.mark.parametrize("separator", ["\n", "\n\n"])
def test_real_lists(marker: str, separator: str) -> None:
    """Keep real list items separate without adding empty paragraphs."""
    source = f"Intro\n{marker}Alpha{separator}{marker}Beta"
    result = md_to_html(source, use_base64=True)
    assert result.count("<li>") == 2
    assert "<p/>" not in result
    assert "<br" not in result
    assert "<p></p>" not in result


@pytest.mark.parametrize("marker", [r"\* ", r"\- ", "-", "*"])
def test_literal_marker_breaks(marker: str) -> None:
    """Separate consecutive literal labels using one hard break per boundary."""
    source = f"{marker}Alpha\n{marker}Beta\n{marker}Gamma"
    result = md_to_html(source, use_base64=True)
    assert result.count("<br") == 2
    assert "<li>" not in result
    normalized = normalize_markdown_spacing(source)
    assert normalize_markdown_spacing(normalized) == normalized


@pytest.mark.parametrize(
    "source",
    [
        "\\* Alpha\n\n\\* Beta",
        "ordinary\nparagraph",
        "*emphasis*\n*more emphasis*",
        "---\n***",
        "- - -\n* * *",
        "-1\n-2",
        "```text\n\\* Alpha\n\\* Beta\n```",
        "~~~~\n-A\n-B\n~~~~",
        "    -A\n    -B",
        "$$\n-A\n-B\n$$",
        "<pre>\n-A\n-B\n</pre>",
        "<!--\n-A\n-B\n-->",
        "- Parent\n    - Child\n    - Another\n- End",
        "\\* Alpha  \n\\* Beta",
        "\\* Alpha<br>\n\\* Beta",
    ],
)
def test_preserved_content(source: str) -> None:
    """Leave existing spacing, non-list syntax, and protected blocks unchanged."""
    assert normalize_markdown_spacing(source) == source


def test_nested_list_structure() -> None:
    """Retain the hierarchy of standard nested lists."""
    result = md_to_html("- Parent\n    - Child\n    - Another\n- End", use_base64=True)
    assert result.count("<ul>") == 2
    assert result.count("<li>") == 4


@pytest.mark.parametrize(
    ("source", "paragraphs", "breaks", "numbered"),
    [
        ("Intro\n- Alpha\n- Beta", 3, 0, 2),
        ("\\* Alpha\n\\* Beta", 1, 1, 0),
        ("\\* Alpha\n\n\\* Beta", 2, 0, 0),
        ("- Alpha\n\n- Beta", 2, 0, 2),
    ],
)
def test_docx_structure(
    tmp_path: Path, source: str, paragraphs: int, breaks: int, numbered: int
) -> None:
    """Verify actual Word paragraphs, hard breaks, and list numbering end to end."""
    md_path = tmp_path / "input.md"
    docx_path = tmp_path / "output.docx"
    md_path.write_text(source, encoding="utf-8")
    md_to_doc(str(md_path), str(docx_path), title="Spacing regression")
    with ZipFile(docx_path) as archive:
        document = ElementTree.fromstring(archive.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    body = document.find("w:body", ns)
    assert body is not None
    word_paragraphs = body.findall("w:p", ns)
    assert "".join(word_paragraphs[0].itertext()).strip() == "Spacing regression"
    assert len(word_paragraphs[1:]) == paragraphs
    assert len(body.findall(".//w:br", ns)) == breaks
    assert len(body.findall(".//w:numPr", ns)) == numbered
    assert all(p.find(".//w:t", ns) is not None for p in body.findall("w:p", ns))


TABLE = "| 기법 | 내용 |\n|---|---|\n| **드롭아웃** | 일부 뉴런 비활성화 |\n| 정규화 | 가중치 패널티 |"


@pytest.mark.parametrize(
    "prefix",
    ["# 제목\n", "**과적합 해결**:\n", "일반 문단\n", "- 항목\n", "1. 항목\n", "> 인용\n", "과소적합 ★ 📝\n"],
)
def test_table_after_any_line(prefix: str) -> None:
    """Render a table as <table> whatever non-blank line precedes it."""
    result = md_to_html(prefix + TABLE, use_base64=True)
    assert result.count("<table") == 1
    assert result.count("<tr>") == 3
    assert "|---|" not in result


def test_table_spacing_idempotent_and_protected() -> None:
    """Do not double-insert blanks, and leave tables inside code fences untouched."""
    once = normalize_markdown_spacing("텍스트\n" + TABLE)
    assert normalize_markdown_spacing(once) == once
    fenced = "```\n텍스트\n" + TABLE + "\n```"
    assert normalize_markdown_spacing(fenced) == fenced
    assert normalize_markdown_spacing(TABLE) == TABLE


def test_docx_table_after_paragraph(tmp_path: Path) -> None:
    """Word output has a real w:tbl for a table directly below a paragraph."""
    md_path = tmp_path / "input.md"
    docx_path = tmp_path / "output.docx"
    md_path.write_text("**과적합 해결**:\n" + TABLE, encoding="utf-8")
    md_to_doc(str(md_path), str(docx_path), title="Table")
    with ZipFile(docx_path) as archive:
        document = ElementTree.fromstring(archive.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    assert len(document.findall(".//w:tbl", ns)) == 1
    assert len(document.findall(".//w:tr", ns)) == 3
