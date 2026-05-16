#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pypandoc
import importlib.util
import argparse
import os
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


def doc_to_html(
    doc_path: str,
    output_path: Optional[str] = None,
    embed_resources: bool = True,
) -> str:
    """DOCX 파일을 HTML로 변환

    Args:
        doc_path: 입력 DOCX 파일 경로
        output_path: 출력 HTML 파일 경로 (None이면 입력 경로 기준 .html)
        embed_resources: True면 이미지를 base64로 임베딩 (단일 파일 HTML)

    Returns:
        출력 HTML 파일 경로
    """
    if not os.path.isfile(doc_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {doc_path}")

    resolved_output = output_path or os.path.splitext(doc_path)[0] + ".html"

    logging.info(f"DOCX 읽기: {doc_path}")

    extra_args = ["--standalone"]
    if embed_resources:
        # pandoc 3.x: --embed-resources, 2.x: --self-contained
        pandoc_ver = pypandoc.get_pandoc_version()
        major = int(pandoc_ver.split(".")[0])
        if major >= 3:
            extra_args.append("--embed-resources")
        else:
            extra_args.append("--self-contained")

    logging.debug("Pandoc docx→html 변환 중...")
    pypandoc.convert_file(
        doc_path,
        "html",
        outputfile=resolved_output,
        extra_args=extra_args,
    )

    logging.info(f"변환 완료: {resolved_output}")
    return resolved_output


def main() -> None:
    parser = argparse.ArgumentParser(description="DOCX(.docx)를 HTML로 변환합니다.")
    parser.add_argument("input", help="입력 DOCX 파일 경로 (.docx)")
    parser.add_argument("-o", "--output", help="출력 HTML 파일 경로 (.html)")
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="이미지를 base64로 임베딩하지 않고 별도 파일로 추출",
    )
    args = parser.parse_args()

    in_path = args.input
    if not os.path.isfile(in_path):
        print(f"파일을 찾을 수 없습니다: {in_path}", file=sys.stderr)
        sys.exit(1)

    doc_to_html(in_path, args.output, embed_resources=not args.no_embed)


if __name__ == "__main__":
    main()
