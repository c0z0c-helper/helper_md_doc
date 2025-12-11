#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import base64
import os
import re
import sys
import logging
from pathlib import Path
from typing import Optional

# 패키지 루트를 sys.path에 추가하여 절대 임포트 통일
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# 의존성 확인 및 설치
import importlib.util

spec = importlib.util.spec_from_file_location(
    "requirements_rnac", os.path.join(os.path.dirname(__file__), "requirements_rnac.py")
)
requirements_rnac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(requirements_rnac)
requirements_rnac.check_and_install_dependencies()

import pypandoc

logging.basicConfig(level=logging.INFO, format="%(message)s")


def embed_images_as_base64(html_text: str, base_dir: str) -> str:
    """
    HTML의 로컬 이미지 경로를 base64 인코딩하여 임베딩.
    Base64로 이미 인코딩된 이미지(data:image/...)는 건드리지 않음.

    Args:
        html_text: 원본 HTML 텍스트
        base_dir: 이미지 파일 기준 디렉토리

    Returns:
        이미지가 base64로 임베딩된 HTML 텍스트
    """

    def replace_img(match):
        img_path = match.group(1)

        # 이미 Base64로 인코딩된 이미지는 건드리지 않음
        if img_path.startswith("data:"):
            return match.group(0)

        img_path = img_path.replace("/", os.sep).replace("\\", os.sep)

        if os.path.isabs(img_path):
            full_path = img_path
        else:
            full_path = os.path.join(base_dir, img_path)

        full_path = os.path.normpath(full_path)

        if not os.path.isfile(full_path):
            logging.warning(f"이미지 파일 없음: {full_path}")
            return match.group(0)

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

        logging.info(f"이미지 임베딩: {os.path.basename(full_path)}")
        return f'<img src="data:{mime_type};base64,{img_data}"'

    pattern = r'<img src="([^"]+)"'
    return re.sub(pattern, replace_img, html_text)


def clean_html_for_pandoc(html_text: str) -> str:
    """
    Pandoc 변환을 위해 HTML 정리: KaTeX 스크립트/링크 제거.

    Args:
        html_text: 원본 HTML 텍스트

    Returns:
        정리된 HTML 텍스트 (수식 블록 $$...$$ 유지)
    """
    html_text = re.sub(r"<link[^>]*katex[^>]*>", "", html_text, flags=re.IGNORECASE)
    html_text = re.sub(
        r"<script[^>]*katex[^>]*>.*?</script>", "", html_text, flags=re.IGNORECASE | re.DOTALL
    )
    html_text = re.sub(
        r"<script[^>]*mermaid[^>]*>.*?</script>", "", html_text, flags=re.IGNORECASE | re.DOTALL
    )

    return html_text


def html_to_doc(html_path: str, output_path: str) -> None:
    """
    HTML 파일을 DOCX로 변환 (이미지/수식 임베딩).

    Args:
        html_path: 입력 HTML 파일 경로
        output_path: 출력 DOCX 파일 경로
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
    pypandoc.convert_text(
        html_text, "docx", format="html", outputfile=output_path, extra_args=["--standalone"]
    )

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
