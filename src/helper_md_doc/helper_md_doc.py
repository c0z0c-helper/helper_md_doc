#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from helper_md_doc.helper_html_doc import clean_html_for_pandoc  # mathml/image 모드에서 사용
from helper_md_doc.helper_md_html import md_to_html, _cleanup_browser, replace_mermaid_with_images
import pypandoc
import importlib.util
import argparse
import os
import re
import sys
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

# 패키지 루트를 sys.path에 추가하여 절대 임포트 통일
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# 의존성 확인 및 설치

<<<<<<< HEAD
if getattr(sys, "frozen", False):
    # frozen 실행 파일: 패키지가 이미 번들됨, 직접 임포트
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
=======
spec = importlib.util.spec_from_file_location(
    "requirements_rnac", os.path.join(
        os.path.dirname(__file__), "requirements_rnac.py")
)
requirements_rnac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(requirements_rnac)
requirements_rnac.check_and_install_dependencies()
>>>>>>> master


logging.basicConfig(level=logging.INFO, format="%(message)s")


def md_to_doc(
    md_path: str,
    output_path: str,
    title: Optional[str] = None,
    reference_doc: Optional[str] = None,
    math_mode: str = "mathml",
) -> None:
    """Markdown 파일을 DOCX로 변환

    Args:
        md_path: 입력 Markdown 파일 경로
        output_path: 출력 DOCX 파일 경로
        title: HTML 문서 제목 (None일 경우 첫 번째 # 헤더 사용)
        reference_doc: 사용자 지정 reference.docx 경로 (None이면 기본값 사용)
        math_mode: 수식 처리 방식
            - "mathml": LaTeX→MathML HTML 삽입 후 html→docx (Pandoc MathML→OMML, 기본)
            - "omml"  : Pandoc md→docx 직접 변환 (수식 네이티브 OMML, 세부 튜닝 불가)
            - "image" : LaTeX→KaTeX PNG 이미지 후 html→docx
    """
    logging.info(f"Markdown 읽기: {md_path}")
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    from helper_md_doc.helper_html_doc import _REFERENCE_DOCX

    ref_doc = reference_doc or _REFERENCE_DOCX

    if math_mode == "omml":
        # Mermaid만 PNG 파일로 치환, LaTeX는 pandoc이 직접 OMML로 변환
        logging.debug("Mermaid 다이어그램 렌더링 중 (omml 모드)...")
        with tempfile.TemporaryDirectory() as tmpdir:
            md_processed = replace_mermaid_with_images(
                md_text, tmpdir, use_base64=False)
            # img src 경로의 Windows 구분자만 / 로 변환 (LaTeX 백슬래시 보존)
            md_processed = re.sub(
                r'(<img\s[^>]*src=")([^"]+)(")',
                lambda m: m.group(
                    1) + m.group(2).replace("\\", "/") + m.group(3),
                md_processed,
            )

            tmp_md = os.path.join(tmpdir, "input.md")
            with open(tmp_md, "w", encoding="utf-8") as f:
                f.write(md_processed)

            logging.debug("Pandoc md→docx 변환 중 (OMML 수식)...")
            extra_args = ["--standalone", "--mathml"]
            if os.path.isfile(ref_doc):
                extra_args.append(f"--reference-doc={ref_doc}")
            pypandoc.convert_file(
                tmp_md, "docx", outputfile=output_path, extra_args=extra_args)
    else:
        # mathml / image 모드: HTML 경유 변환
        logging.debug(f"Markdown → HTML 변환 중 (math_mode={math_mode})...")
        html_text = md_to_html(md_text, title=title,
                               use_base64=True, math_mode=math_mode)

        logging.debug(f"HTML 정리 중 (스크립트 태그 제거)...")
        html_text = clean_html_for_pandoc(html_text)

        logging.debug("HTML → DOCX 변환 중...")
        extra_args = ["--standalone"]
        if os.path.isfile(ref_doc):
            extra_args.append(f"--reference-doc={ref_doc}")
        pypandoc.convert_text(
            html_text, "docx", format="html", outputfile=output_path, extra_args=extra_args
        )

        logging.debug("overline 수식 교정 중...")
        from helper_md_doc.helper_html_doc import fix_overline_in_docx
        fix_overline_in_docx(output_path)

    _cleanup_browser()
    logging.info(f"변환 완료: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Markdown(.md)을 DOCX로 변환합니다 (Mermaid/LaTeX 포함)."
    )
    parser.add_argument("input", help="입력 Markdown 파일 경로 (.md)")
    parser.add_argument("-o", "--output", help="출력 DOCX 파일 경로 (.docx)")
    parser.add_argument("--title", default=None, help="문서 제목")
    parser.add_argument("--reference-doc", default=None,
                        help="서식 템플릿 reference.docx 경로")
    parser.add_argument(
        "--math-mode",
        choices=["omml", "mathml", "image"],
        default="mathml",
        help="수식 처리 방식: mathml=MathML→OMML(기본), omml=Pandoc 네이티브 OMML(세부 튜닝 불가), image=KaTeX PNG",
    )
    args = parser.parse_args()

    in_path = args.input
    if not os.path.isfile(in_path):
        print(f"파일을 찾을 수 없습니다: {in_path}", file=sys.stderr)
        sys.exit(1)

    out_path = args.output or os.path.splitext(in_path)[0] + ".docx"
    title = args.title or os.path.splitext(os.path.basename(in_path))[0]

    md_to_doc(in_path, out_path, title,
              reference_doc=args.reference_doc, math_mode=args.math_mode)


if __name__ == "__main__":
    main()
