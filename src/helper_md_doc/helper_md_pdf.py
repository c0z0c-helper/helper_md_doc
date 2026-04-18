#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import importlib.util

spec = importlib.util.spec_from_file_location(
    "requirements_rnac", os.path.join(os.path.dirname(__file__), "requirements_rnac.py")
)
requirements_rnac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(requirements_rnac)
requirements_rnac.check_and_install_dependencies()

from helper_md_doc.helper_html_pdf import _html_text_to_pdf
from helper_md_doc.helper_md_html import _cleanup_browser, md_to_html

logging.basicConfig(level=logging.INFO, format="%(message)s")


def md_to_pdf(md_path: str, output_path: Optional[str] = None, title: Optional[str] = None) -> str:
    logging.info(f"Markdown 읽기: {md_path}")
    with open(md_path, "r", encoding="utf-8") as file:
        md_text = file.read()

    resolved_output_path = output_path or os.path.splitext(md_path)[0] + ".pdf"
    resolved_title = title or os.path.splitext(os.path.basename(md_path))[0]
    base_dir = os.path.dirname(os.path.abspath(md_path))

    try:
        html_text = md_to_html(md_text, title=resolved_title, use_base64=True)
        return _html_text_to_pdf(html_text, resolved_output_path, base_dir=base_dir)
    finally:
        _cleanup_browser()


def main() -> None:
    parser = argparse.ArgumentParser(description="Markdown(.md)을 PDF로 변환합니다.")
    parser.add_argument("input", help="입력 Markdown 파일 경로 (.md)")
    parser.add_argument("-o", "--output", help="출력 PDF 파일 경로 (.pdf)")
    parser.add_argument("--title", default=None, help="문서 제목")
    args = parser.parse_args()

    in_path = args.input
    if not os.path.isfile(in_path):
        print(f"파일을 찾을 수 없습니다: {in_path}", file=sys.stderr)
        sys.exit(1)

    md_to_pdf(in_path, args.output, args.title)


if __name__ == "__main__":
    main()
