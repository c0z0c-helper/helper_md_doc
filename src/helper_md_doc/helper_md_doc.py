#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import logging
import pypandoc
from typing import Optional
try:
    from .helper_md_html import md_to_html, _cleanup_browser
    from .helper_html_doc import clean_html_for_pandoc
except ImportError:
    from helper_md_html import md_to_html, _cleanup_browser
    from helper_html_doc import clean_html_for_pandoc

logging.basicConfig(level=logging.INFO, format='%(message)s')


def md_to_doc(md_path: str, output_path: str, title: Optional[str] = None) -> None:
    """Markdown 파일을 DOCX로 변환 (Mermaid/LaTeX를 Base64 PNG로 임베딩)
    
    Args:
        md_path: 입력 Markdown 파일 경로
        output_path: 출력 DOCX 파일 경로
        title: HTML 문서 제목 (None일 경우 첫 번째 # 헤더 사용)
    """
    logging.info(f"Markdown 읽기: {md_path}")
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()
    
    logging.debug("Markdown -> HTML 변환 중 (Mermaid/LaTeX -> Base64 PNG)...")
    html_text = md_to_html(md_text, title=title, use_base64=True)
    
    logging.debug("HTML 정리 중 (스크립트 태그 제거)...")
    html_text = clean_html_for_pandoc(html_text)
    
    logging.debug("HTML -> DOCX 변환 중...")
    pypandoc.convert_text(
        html_text,
        'docx',
        format='html',
        outputfile=output_path,
        extra_args=['--standalone']
    )
    
    _cleanup_browser()
    logging.info(f"변환 완료: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Markdown(.md)을 DOCX로 변환합니다 (Mermaid/LaTeX 이미지 임베딩)."
    )
    parser.add_argument("input", help="입력 Markdown 파일 경로 (.md)")
    parser.add_argument("-o", "--output", help="출력 DOCX 파일 경로 (.docx)")
    parser.add_argument("--title", default=None, help="문서 제목")
    args = parser.parse_args()

    in_path = args.input
    if not os.path.isfile(in_path):
        print(f"파일을 찾을 수 없습니다: {in_path}", file=sys.stderr)
        sys.exit(1)

    out_path = args.output or os.path.splitext(in_path)[0] + ".docx"
    title = args.title or os.path.splitext(os.path.basename(in_path))[0]
    
    md_to_doc(in_path, out_path, title)


if __name__ == "__main__":
    main()
