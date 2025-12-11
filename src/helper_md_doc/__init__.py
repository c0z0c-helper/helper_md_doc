"""
helper-md-doc
=============

Markdown/HTML을 DOCX로 변환하는 문서 변환 라이브러리

주요 기능:
- Markdown → HTML 변환 (Mermaid 다이어그램, LaTeX 수식 지원)
- HTML → DOCX 변환 (이미지/수식 임베딩)
- Markdown → DOCX 직접 변환
- Playwright 기반 Mermaid/KaTeX 렌더링
- Base64 인코딩 또는 파일 기반 이미지 처리

기본 사용법:
    from helper_md_doc import md_to_html, html_to_doc, md_to_doc

    # Markdown → HTML
    html = md_to_html(md_text, title="문서 제목")

    # HTML → DOCX
    html_to_doc("input.html", "output.docx")

    # Markdown → DOCX (원스텝)
    md_to_doc("input.md", "output.docx")
"""

__version__ = "0.5.5"

import os
import importlib.util

spec = importlib.util.spec_from_file_location(
    "requirements_rnac", os.path.join(os.path.dirname(__file__), "requirements_rnac.py")
)
requirements_rnac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(requirements_rnac)
requirements_rnac.check_and_print_dependencies()

from .helper_md_html import md_to_html
from .helper_html_doc import html_to_doc, clean_html_for_pandoc, embed_images_as_base64
from .helper_md_doc import md_to_doc

__all__ = [
    "md_to_html",
    "html_to_doc",
    "md_to_doc",
    "clean_html_for_pandoc",
    "embed_images_as_base64",
    "__version__",
]
