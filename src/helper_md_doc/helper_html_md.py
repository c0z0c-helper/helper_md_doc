#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pypandoc
import importlib.util
import argparse
import os
import re
import sys
import logging
from pathlib import Path
from typing import Optional

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


if getattr(sys, "frozen", False):
    from helper_md_doc import requirements_rnac
    requirements_rnac.check_and_install_dependencies()
else:
    spec = importlib.util.spec_from_file_location(
        "requirements_rnac", os.path.join(
            os.path.dirname(__file__), "requirements_rnac.py")
    )
    requirements_rnac = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(requirements_rnac)
    requirements_rnac.check_and_install_dependencies()


logging.basicConfig(level=logging.INFO, format="%(message)s")


def _clean_html_for_md(html_text: str) -> str:
    """Markdown 변환 전 HTML 정리: script/style 제거"""
    html_text = re.sub(r"<style\b[^>]*>.*?</style>",
                       "", html_text, flags=re.IGNORECASE | re.DOTALL)
    html_text = re.sub(
        r"<script\b[^>]*>.*?</script>", "", html_text, flags=re.IGNORECASE | re.DOTALL
    )
    return html_text


def html_to_md(
    html_path: str,
    output_path: Optional[str] = None,
    md_variant: str = "markdown",
) -> str:
    """HTML 파일을 Markdown으로 변환

    Args:
        html_path: 입력 HTML 파일 경로
        output_path: 출력 Markdown 파일 경로 (None이면 입력 경로 기준 .md)
        md_variant: 출력 Markdown 방언
            - "markdown"         : pandoc 기본 Markdown (기본)
            - "gfm"              : GitHub Flavored Markdown
            - "markdown_strict"  : 표준 Markdown

    Returns:
        출력 Markdown 파일 경로

    Note:
        MathML 수식은 LaTeX로 부분 복원됩니다.
        Mermaid 다이어그램은 PNG 이미지 참조로 남으며 원본 코드는 복원되지 않습니다.
    """
    if not os.path.isfile(html_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {html_path}")

    resolved_output = output_path or os.path.splitext(html_path)[0] + ".md"

    logging.info(f"HTML 읽기: {html_path}")
    with open(html_path, "r", encoding="utf-8") as f:
        html_text = f.read()

    logging.debug("HTML 정리 중 (script/style 제거)...")
    html_text = _clean_html_for_md(html_text)

    logging.debug(f"Pandoc html→{md_variant} 변환 중...")
    md_text = pypandoc.convert_text(
        html_text,
        md_variant,
        format="html",
        extra_args=["--wrap=none"],
    )

    with open(resolved_output, "w", encoding="utf-8") as f:
        f.write(md_text)

    logging.info(f"변환 완료: {resolved_output}")
    return resolved_output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HTML(.html)을 Markdown으로 변환합니다.")
    parser.add_argument("input", help="입력 HTML 파일 경로 (.html)")
    parser.add_argument("-o", "--output", help="출력 Markdown 파일 경로 (.md)")
    parser.add_argument(
        "--variant",
        choices=["markdown", "gfm", "markdown_strict"],
        default="markdown",
        help="출력 Markdown 방언: markdown(기본), gfm, markdown_strict",
    )
    args = parser.parse_args()

    in_path = args.input
    if not os.path.isfile(in_path):
        print(f"파일을 찾을 수 없습니다: {in_path}", file=sys.stderr)
        sys.exit(1)

    html_to_md(in_path, args.output, md_variant=args.variant)


if __name__ == "__main__":
    main()
