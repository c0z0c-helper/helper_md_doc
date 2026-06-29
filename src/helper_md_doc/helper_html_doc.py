#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTML → DOCX 변환: 이미지 임베딩, HTML 정리, Pandoc 변환"""

import pypandoc
import importlib.util
import argparse
import base64
import os
import re
import sys
import logging
from pathlib import Path
from typing import Optional

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

spec = importlib.util.spec_from_file_location(
    "requirements_rnac", os.path.join(os.path.dirname(__file__), "requirements_rnac.py")
)
requirements_rnac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(requirements_rnac)
requirements_rnac.check_and_install_dependencies()

from helper_md_doc.helper_docx_fix import fix_tables_in_docx, fix_overline_in_docx

logging.basicConfig(level=logging.INFO, format="%(message)s")

# 패키지 내장 reference.docx 경로 (Code Fence 스타일 정의 포함)
_REFERENCE_DOCX = os.path.join(os.path.dirname(__file__), "reference.docx")


def embed_images_as_base64(html_text: str, base_dir: Optional[str] = None) -> str:
    """HTML의 로컬 이미지 경로를 base64 인코딩하여 임베딩.
    Base64로 이미 인코딩된 이미지(data:image/...)는 건드리지 않음.

    Args:
        html_text: 원본 HTML 텍스트
        base_dir: 이미지 파일 기준 디렉토리

    Returns:
        이미지가 base64로 임베딩된 HTML 텍스트
    """

    def replace_src(match):
        """<img> 태그 전체를 받아 src 속성값만 교체"""
        full_tag = match.group(0)
        src_match = re.search(r'src="([^"]+)"', full_tag)
        if not src_match:
            return full_tag
        img_path = src_match.group(1)

        if img_path.startswith("data:"):
            return full_tag

        img_path_os = img_path.replace("/", os.sep).replace("\\", os.sep)
        if os.path.isabs(img_path_os):
            full_path = img_path_os
        else:
            full_path = os.path.join(base_dir or "", img_path_os)
        full_path = os.path.normpath(full_path)

        if not os.path.isfile(full_path):
            logging.warning(f"이미지 파일 없음: {full_path}")
            return full_tag

        ext = os.path.splitext(full_path)[1].lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".bmp": "image/bmp",
        }
        mime_type = mime_map.get(ext, "image/png")

        with open(full_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("utf-8")

        logging.debug(f"이미지 임베딩: {os.path.basename(full_path)}")
        new_src = f"data:{mime_type};base64,{img_data}"
        return full_tag[:src_match.start(1)] + new_src + full_tag[src_match.end(1):]

    # <img> 태그 전체를 매칭하여 src 속성만 교체 (alt 등 다른 속성 순서 무관)
    return re.sub(r'<img\s[^>]+>', replace_src, html_text)


def clean_html_for_pandoc(html_text: str) -> str:
    """Pandoc 변환을 위해 HTML 정리: KaTeX 스크립트/링크 제거 및 코드블록 래핑.

    Args:
        html_text: 원본 HTML 텍스트

    Returns:
        정리된 HTML 텍스트
    """
    html_text = re.sub(r"<style\b[^>]*>.*?</style>",
                       "", html_text, flags=re.IGNORECASE | re.DOTALL)
    html_text = re.sub(
        r"<script\b[^>]*>.*?</script>", "", html_text, flags=re.IGNORECASE | re.DOTALL
    )
    html_text = re.sub(r"<link[^>]*katex[^>]*>", "", html_text, flags=re.IGNORECASE)
    html_text = re.sub(
        r"<script[^>]*katex[^>]*>.*?</script>", "", html_text, flags=re.IGNORECASE | re.DOTALL
    )
    html_text = re.sub(
        r"<script[^>]*mermaid[^>]*>.*?</script>", "", html_text, flags=re.IGNORECASE | re.DOTALL
    )

    def wrap_pre_block(match: re.Match) -> str:
        inner = match.group(1)
        inner = (
            inner.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
        )
        lines = inner.split("\n")
        while lines and not lines[-1].strip():
            lines.pop()

        def preserve_indent(line: str) -> str:
            if not line:
                return "&#160;"
            stripped = line.lstrip()
            indent = line[: len(line) - len(stripped)]
            nbsp_indent = indent.replace("\t", "&#160;&#160;&#160;&#160;").replace(" ", "&#160;")
            return nbsp_indent + stripped

        p_lines = "".join(f"<p>{preserve_indent(line)}</p>" for line in lines)
        return f'<div custom-style="Code Fence">{p_lines}</div>'

    html_text = re.sub(
        r"<pre><code[^>]*>(.*?)</code></pre>",
        wrap_pre_block,
        html_text,
        flags=re.DOTALL,
    )

    html_text = re.sub(
        r'<div style="text-align: center;[^"]*">(<img [^>]+/>)</div>',
        r'<div custom-style="Image Center">\1</div>',
        html_text,
    )

    def wrap_table_cell(m: re.Match) -> str:
        tag = m.group(1)          # "td" 또는 "th"
        attrs = m.group(2) or ""  # class, colspan 등 속성
        inner = m.group(3)        # 셀 내부 HTML
        return f'<{tag}{attrs}><div custom-style="In Table">{inner}</div></{tag}>'

    html_text = re.sub(
        r'<(t[dh])(\s[^>]*)?>(.+?)</\1>',
        wrap_table_cell,
        html_text,
        flags=re.DOTALL,
    )

    return html_text


def html_to_doc(html_path: str, output_path: str, reference_doc: Optional[str] = None) -> None:
    """HTML 파일을 DOCX로 변환 (이미지/수식 임베딩).

    Args:
        html_path: 입력 HTML 파일 경로
        output_path: 출력 DOCX 파일 경로
        reference_doc: 사용자 지정 reference.docx 경로 (None이면 기본값 사용)
    """
    logging.info(f"HTML 읽기: {html_path}")
    with open(html_path, "r", encoding="utf-8") as f:
        html_text = f.read()

    base_dir = os.path.dirname(os.path.abspath(html_path))

    logging.debug("이미지 임베딩 중...")
    html_text = embed_images_as_base64(html_text, base_dir)

    logging.debug("HTML 정리 중...")
    html_text = clean_html_for_pandoc(html_text)

    logging.debug("DOCX 변환 중...")
    ref_doc = reference_doc or _REFERENCE_DOCX
    extra_args = ["--standalone"]
    if os.path.isfile(ref_doc):
        extra_args.append(f"--reference-doc={ref_doc}")
    pypandoc.convert_text(
        html_text, "docx", format="html", outputfile=output_path, extra_args=extra_args
    )

    logging.debug("표 스타일/테두리/정렬 교정 중...")
    fix_tables_in_docx(output_path)

    logging.debug("overline 수식 교정 중...")
    fix_overline_in_docx(output_path)

    logging.info(f"변환 완료: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="HTML(.html)을 DOCX로 변환합니다 (이미지/수식 임베딩)."
    )
    parser.add_argument("input", help="입력 HTML 파일 경로 (.html)")
    parser.add_argument("-o", "--output", help="출력 DOCX 파일 경로 (.docx)")
    args = parser.parse_args()

    in_path = args.input
    if not os.path.isfile(in_path):
        print(f"파일을 찾을 수 없습니다: {in_path}", file=sys.stderr)
        sys.exit(1)

    out_path = args.output or os.path.splitext(in_path)[0] + ".docx"
    html_to_doc(in_path, out_path)


if __name__ == "__main__":
    main()
