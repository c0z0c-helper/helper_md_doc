"""Tests for HTML to PDF conversion"""

from pathlib import Path

import pytest

from helper_md_doc import html_to_pdf


def test_html_to_pdf_basic(tmp_path: Path, require_chromium) -> None:
    html_path = tmp_path / "sample.html"
    html_path.write_text(
        "<html><body><h1>테스트</h1><p>PDF 변환</p></body></html>", encoding="utf-8"
    )

    output_path = tmp_path / "output.pdf"
    result_path = html_to_pdf(str(html_path), str(output_path))

    assert result_path == str(output_path)
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_html_to_pdf_default_output_path(tmp_path: Path, require_chromium) -> None:
    html_path = tmp_path / "default.html"
    html_path.write_text("<html><body><p>기본 출력 경로</p></body></html>", encoding="utf-8")

    result_path = html_to_pdf(str(html_path))
    expected_path = html_path.with_suffix(".pdf")

    assert result_path == str(expected_path)
    assert expected_path.exists()
    assert expected_path.stat().st_size > 0


def test_html_to_pdf_file_not_found(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.html"

    with pytest.raises(FileNotFoundError):
        html_to_pdf(str(missing_path))
