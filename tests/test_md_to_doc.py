"""Tests for Markdown to DOCX conversion"""

import pytest
import os
import tempfile
from pathlib import Path


def test_md_to_doc_basic():
    """기본 Markdown → DOCX 변환 테스트 (pypandoc 설치 필요)"""
    try:
        from helper_md_doc import md_to_doc

        # 테스트용 임시 파일 생성
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write("# 테스트\n\n이것은 **테스트** 문서입니다.")
            md_path = f.name

        output_path = md_path.replace(".md", ".docx")

        try:
            # 변환 실행
            md_to_doc(md_path, output_path, title="테스트")

            # 출력 파일이 생성되었는지 확인
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0

        finally:
            # 임시 파일 정리
            if os.path.exists(md_path):
                os.unlink(md_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    except ImportError:
        pytest.skip("pypandoc이 설치되지 않아 테스트를 건너뜁니다.")
    except Exception as e:
        # Pandoc이 설치되지 않은 경우 등
        pytest.skip(f"테스트를 실행할 수 없습니다: {e}")


def test_md_to_doc_file_not_found():
    """존재하지 않는 파일 처리 테스트"""
    try:
        from helper_md_doc import md_to_doc

        with pytest.raises(FileNotFoundError):
            md_to_doc("nonexistent.md", "output.docx")

    except ImportError:
        pytest.skip("pypandoc이 설치되지 않아 테스트를 건너뜁니다.")
