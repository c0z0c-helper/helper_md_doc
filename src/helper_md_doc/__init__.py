"""
helper-md-doc
=============

Markdown/HTML/DOCX 문서 변환 라이브러리

순방향 변환:
- Markdown → HTML 변환 (Mermaid 다이어그램, LaTeX 수식 지원)
- Markdown → DOCX 직접 변환
- Markdown → PDF 변환
- HTML → DOCX 변환 (이미지/수식 임베딩)
- HTML → PDF 변환

역방향 변환:
- DOCX → HTML 변환 (이미지 base64 임베딩)
- HTML → Markdown 변환
- Markdown → 순수 텍스트 변환

기본 사용법:
    from helper_md_doc import md_to_html, html_to_doc, md_to_doc
    from helper_md_doc import doc_to_html, html_to_md, md_to_text

    # Markdown → HTML
    html = md_to_html(md_text, title="문서 제목")

    # HTML → DOCX
    html_to_doc("input.html", "output.docx")

    # Markdown → DOCX (원스텝)
    md_to_doc("input.md", "output.docx")

    # DOCX → HTML (역변환)
    doc_to_html("input.docx", "output.html")

    # HTML → Markdown (역변환)
    html_to_md("input.html", "output.md")

    # Markdown → 순수 텍스트 (역변환)
    md_to_text("input.md", "output.txt")
"""

from helper_md_doc.helper_md_text import md_to_text
from helper_md_doc.helper_html_md import html_to_md
from helper_md_doc.helper_doc_html import doc_to_html
from helper_md_doc.helper_md_pdf import md_to_pdf
from helper_md_doc.helper_md_doc import md_to_doc
from helper_md_doc.helper_html_pdf import html_to_pdf
from helper_md_doc.helper_html_doc import html_to_doc, clean_html_for_pandoc, embed_images_as_base64
from helper_md_doc.helper_md_html import md_to_html
__version__ = "0.5.16"

import os
import sys
from pathlib import Path
import importlib.util

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

spec = importlib.util.spec_from_file_location(
    "requirements_rnac", os.path.join(
        os.path.dirname(__file__), "requirements_rnac.py")
)
requirements_rnac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(requirements_rnac)
requirements_rnac.check_and_print_dependencies()


__all__ = [
    # 순방향
    "md_to_html",
    "html_to_doc",
    "html_to_pdf",
    "md_to_doc",
    "md_to_pdf",
    # 역방향
    "doc_to_html",
    "html_to_md",
    "md_to_text",
    # 유틸
    "clean_html_for_pandoc",
    "embed_images_as_base64",
    "__version__",
]
