"""Tests for Markdown to PDF conversion"""

from pathlib import Path

import pytest

from helper_md_doc import md_to_pdf


def test_md_to_pdf_basic(tmp_path: Path, require_chromium) -> None:
    md_path = tmp_path / "sample.md"
    md_path.write_text("# 테스트\n\n이것은 **PDF** 변환입니다.", encoding="utf-8")

    output_path = tmp_path / "output.pdf"
    result_path = md_to_pdf(str(md_path), str(output_path), title="테스트")

    assert result_path == str(output_path)
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_md_to_pdf_default_output_path(tmp_path: Path, require_chromium) -> None:
    md_path = tmp_path / "default.md"
    md_path.write_text("# 기본 출력\n\n본문", encoding="utf-8")

    result_path = md_to_pdf(str(md_path))
    expected_path = md_path.with_suffix(".pdf")

    assert result_path == str(expected_path)
    assert expected_path.exists()
    assert expected_path.stat().st_size > 0


def test_md_to_pdf_file_not_found(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.md"

    with pytest.raises(FileNotFoundError):
        md_to_pdf(str(missing_path))
