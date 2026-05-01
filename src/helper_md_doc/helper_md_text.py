#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import logging
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

import pypandoc

logging.basicConfig(level=logging.INFO, format="%(message)s")


def md_to_text(
    md_path: str,
    output_path: Optional[str] = None,
    keep_math: bool = False,
) -> str:
    """Markdown 파일을 순수 텍스트로 변환

    Markdown 문법, HTML 태그, 수식 기호를 제거하고 읽기 쉬운 평문을 생성합니다.

    Args:
        md_path: 입력 Markdown 파일 경로
        output_path: 출력 텍스트 파일 경로 (None이면 입력 경로 기준 .txt)
        keep_math: True면 LaTeX 수식을 원문($...$) 그대로 유지, False면 제거

    Returns:
        출력 텍스트 파일 경로
    """
    if not os.path.isfile(md_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {md_path}")

    resolved_output = output_path or os.path.splitext(md_path)[0] + ".txt"

    logging.info(f"Markdown 읽기: {md_path}")
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    logging.debug("Pandoc md→plain 변환 중...")
    extra_args = ["--wrap=none"]
    if not keep_math:
        # 수식 블록($$...$$) 제거
        import re

        md_text = re.sub(r"\$\$.*?\$\$", "", md_text, flags=re.DOTALL)
        # 인라인 수식($...$) 제거
        md_text = re.sub(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", "", md_text)

    plain_text = pypandoc.convert_text(
        md_text,
        "plain",
        format="markdown",
        extra_args=extra_args,
    )

    with open(resolved_output, "w", encoding="utf-8") as f:
        f.write(plain_text)

    logging.info(f"변환 완료: {resolved_output}")
    return resolved_output


def main() -> None:
    parser = argparse.ArgumentParser(description="Markdown(.md)을 순수 텍스트(.txt)로 변환합니다.")
    parser.add_argument("input", help="입력 Markdown 파일 경로 (.md)")
    parser.add_argument("-o", "--output", help="출력 텍스트 파일 경로 (.txt)")
    parser.add_argument(
        "--keep-math",
        action="store_true",
        help="LaTeX 수식($...$)을 원문 그대로 유지 (기본: 제거)",
    )
    args = parser.parse_args()

    in_path = args.input
    if not os.path.isfile(in_path):
        print(f"파일을 찾을 수 없습니다: {in_path}", file=sys.stderr)
        sys.exit(1)

    md_to_text(in_path, args.output, keep_math=args.keep_math)


if __name__ == "__main__":
    main()
