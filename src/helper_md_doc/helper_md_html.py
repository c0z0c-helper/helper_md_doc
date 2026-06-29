#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import markdown
import importlib.util
import argparse
import html
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

from helper_md_doc.helper_render import (
    _cleanup_browser,
    render_mermaid_to_png,
    render_mermaid_base64,
    render_latex_to_png,
    render_latex_base64,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", Arial, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; font-size: 10pt; line-height: 1.6; padding: 1rem 2rem; max-width: 100%; margin: 0; box-sizing: border-box; }}
        p {{ margin: 0.4em 0 0.6em; }}
        pre {{ background: #f6f8fa; padding: 1rem; border-radius: 6px; white-space: pre-wrap; word-break: break-word; overflow-wrap: break-word; margin: 0.8em 0; }}
        code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; font-size: 0.9em; word-break: break-word; overflow-wrap: break-word; background: #f0f0f0; padding: 0.1em 0.35em; border-radius: 3px; }}
        pre code {{ background: none; padding: 0; border-radius: 0; }}
        blockquote {{ margin: 0.8em 0; padding: 0.4em 1em; border-left: 4px solid #c8d0d8; background: #f9f9f9; color: #555; }}
        hr {{ border: none; border-top: 1px solid #ddd; margin: 1.2em 0; }}
        a {{ color: #1a6ea8; text-decoration: none; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; table-layout: auto; }}
        th, td {{ border: 1px solid #ddd; padding: 0.4rem 0.5rem; text-align: left; word-break: break-word; overflow-wrap: break-word; vertical-align: top; min-width: 3em; max-width: 30em; font-size: 8pt; }}
        th {{ background: #eef1f5; font-weight: 600; }}
        tbody tr:nth-child(even) {{ background: #f9fafb; }}
        .mermaid {{ margin: 1rem 0; }}
        img {{ max-width: 100%; height: auto; display: block; page-break-inside: avoid; }}
        h1 {{ font-size: 16pt; margin: 0.6em 0 0.3em; padding-bottom: 0.2em; border-bottom: 2px solid #ddd; }}
        h2 {{ font-size: 15pt; margin: 0.6em 0 0.3em; padding-bottom: 0.15em; border-bottom: 1px solid #e8e8e8; }}
        h3 {{ font-size: 14pt; margin: 0.5em 0 0.3em; }}
        h4 {{ font-size: 13pt; margin: 0.5em 0 0.2em; }}
        h5 {{ font-size: 12pt; margin: 0.4em 0 0.2em; }}
        h6 {{ font-size: 11pt; margin: 0.4em 0 0.2em; color: #555; }}
        h1, h2, h3, h4, h5, h6 {{ page-break-after: avoid; }}
        tr {{ page-break-inside: avoid; }}
        @media print {{
            body {{ padding: 0; }}
            pre {{ white-space: pre-wrap; }}
            a {{ color: #1a6ea8; }}
        }}
  </style>
  {scripts}
</head>
<body>
{content}
</body>
</html>
"""


def is_simple_text(text: str) -> bool:
    """LaTeX 명령어가 없는 단순 텍스트인지 판별

    Args:
        text: 검사할 텍스트

    Returns:
        True면 단순 텍스트, False면 LaTeX 수식
    """
    latex_patterns = [r"\\[a-zA-Z]+", r"[_^{}]", r"\\[^a-zA-Z]"]
    for pattern in latex_patterns:
        if re.search(pattern, text):
            return False
    return True


def is_list_or_special_line(line: str) -> bool:
    """라인이 리스트 항목이나 특수 패턴으로 시작하는지 확인

    Args:
        line: 검사할 라인

    Returns:
        True면 리스트/특수 라인, False면 일반 텍스트
    """
    stripped = line.lstrip()
    if stripped.startswith(("- ", "* ", "+ ")):
        return True
    if re.match(r"^\d+\.\s", stripped):
        return True
    if stripped.startswith("#"):
        return True
    if re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", stripped):
        return True
    return False


def normalize_markdown_spacing(md_text: str) -> str:
    """Markdown 리스트 앞에 빈 줄 추가 및 이스케이프된 볼드 마커 복원 (python-markdown 호환성)"""
    if md_text and md_text[0] == "\ufeff":
        md_text = md_text[1:]

    md_text = re.sub(r"\\\*\\\*([^*]+?)\\\*\\\*", r"**\1**", md_text)

    lines = md_text.split("\n")
    result_lines = []

    for i, line in enumerate(lines):
        result_lines.append(line)

        if i < len(lines) - 1 and line.strip():
            next_line = lines[i + 1]
            if not next_line.strip():
                continue
            if is_list_or_special_line(line) and not re.match(
                r"^(-{3,}|\*{3,}|_{3,})\s*$", line.lstrip()
            ):
                continue
            if is_list_or_special_line(next_line):
                result_lines.append("<p/>")

    result = "\n".join(result_lines)
    result = re.sub(r"(<br/>|<p/>)(\n(<br/>|<p/>))+", "<p/>", result)
    return result


def replace_mermaid_with_images(
    md_text: str, output_dir: str = "mermaid_diagrams", use_base64: bool = False
) -> str:
    """Markdown의 Mermaid 코드 블록을 이미지로 변환

    Args:
        md_text: Markdown 텍스트
        output_dir: PNG 파일 저장 디렉토리 (use_base64=True일 때 미사용)
        use_base64: True면 Base64로 인코딩, False면 파일 경로 사용

    Returns:
        Mermaid 블록이 이미지로 치환된 Markdown
    """
    if not use_base64:
        os.makedirs(output_dir, exist_ok=True)

    pattern = r"```mermaid\n(.*?)```"
    diagram_count = [0]

    def replace_block(match):
        mermaid_code = match.group(1).strip()
        diagram_count[0] += 1
        logging.debug(f"Mermaid 다이어그램 {diagram_count[0]} 렌더링 중...")

        if use_base64:
            img_src = render_mermaid_base64(mermaid_code)
        else:
            png_filename = f"diagram_{diagram_count[0]:03d}.png"
            png_path = os.path.join(output_dir, png_filename)
            render_mermaid_to_png(mermaid_code, png_path)
            img_src = f"{output_dir}/{png_filename}"

        return f'<img src="{img_src}" alt="Mermaid Diagram {diagram_count[0]}" style="max-width: 100%;" />'

    return re.sub(pattern, replace_block, md_text, flags=re.DOTALL)


def replace_latex_with_images(
    md_text: str, output_dir: str = "latex_equations", use_base64: bool = False
) -> str:
    """Markdown의 LaTeX 수식을 PNG 이미지로 변환

    Args:
        md_text: Markdown 텍스트
        output_dir: PNG 파일 저장 디렉토리 (use_base64=True일 때 미사용)
        use_base64: True면 Base64로 인코딩, False면 파일 경로 사용

    Returns:
        LaTeX 수식이 이미지로 치환된 Markdown
    """
    if not use_base64:
        os.makedirs(output_dir, exist_ok=True)

    equation_count = [0]

    def replace_display_math(match):
        latex_code = match.group(1).strip()
        if is_simple_text(latex_code):
            return f'<div style="text-align: center; margin: 1rem 0; font-weight: bold;">{latex_code}</div>'
        equation_count[0] += 1
        logging.debug(f"블록 수식 {equation_count[0]} 렌더링 중...")
        if use_base64:
            img_src = render_latex_base64(latex_code, display_mode=True)
        else:
            png_filename = f"eq_display_{equation_count[0]:03d}.png"
            png_path = os.path.join(output_dir, png_filename)
            render_latex_to_png(latex_code, png_path, display_mode=True)
            img_src = f"{output_dir}/{png_filename}"
        return f'<div style="text-align: center; margin: 1rem 0;"><img src="{img_src}" alt="Equation {equation_count[0]}" style="display: block; margin: 0 auto;" /></div>'

    def replace_inline_math(match):
        latex_code = match.group(1).strip()
        if is_simple_text(latex_code):
            return f"<code>{latex_code}</code>"
        equation_count[0] += 1
        logging.debug(f"인라인 수식 {equation_count[0]} 렌더링 중...")
        if use_base64:
            img_src = render_latex_base64(latex_code, display_mode=False)
        else:
            png_filename = f"eq_inline_{equation_count[0]:03d}.png"
            png_path = os.path.join(output_dir, png_filename)
            render_latex_to_png(latex_code, png_path, display_mode=False)
            img_src = f"{output_dir}/{png_filename}"
        return f'<img src="{img_src}" alt="Equation {equation_count[0]}" style="display: inline-block; vertical-align: middle;" />'

    md_text = re.sub(r"\$\$(.*?)\$\$", replace_display_math, md_text, flags=re.DOTALL)
    md_text = re.sub(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", replace_inline_math, md_text)
    return md_text


def replace_latex_with_mathml(md_text: str) -> str:
    """Markdown의 LaTeX 수식을 MathML HTML 태그로 변환 (pandoc의 MathML→OMML 변환 활용)

    Args:
        md_text: Markdown 텍스트

    Returns:
        LaTeX 수식이 MathML 태그로 치환된 Markdown
    """
    import latex2mathml.converter

    def _fix_mathml_overline(mathml: str) -> str:
        mathml = re.sub(
            r'<mo\s+accent="true">(?:&#x0*2015;|\u2015)</mo>',
            '<mo stretchy="true">\u00af</mo>',
            mathml,
        )
        mathml = re.sub(r'(<mover)\s+accent="true"', r'\1', mathml)
        return mathml

    def replace_display_math(match):
        latex_code = match.group(1).strip()
        if is_simple_text(latex_code):
            return f'<div style="text-align: center; margin: 1rem 0; font-weight: bold;">{latex_code}</div>'
        mathml = latex2mathml.converter.convert(latex_code, display="block")
        mathml = _fix_mathml_overline(mathml)
        return f'<div style="text-align: center; margin: 1rem 0;">{mathml}</div>'

    def replace_inline_math(match):
        latex_code = match.group(1).strip()
        if is_simple_text(latex_code):
            return f"<code>{latex_code}</code>"
        mathml = latex2mathml.converter.convert(latex_code, display="inline")
        mathml = _fix_mathml_overline(mathml)
        return mathml

    md_text = re.sub(r"\$\$(.*?)\$\$", replace_display_math, md_text, flags=re.DOTALL)
    md_text = re.sub(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", replace_inline_math, md_text)
    return md_text


def md_to_html(
    md_text: str,
    title: Optional[str] = None,
    use_base64: bool = False,
    math_mode: str = "image",
    md_dir: Optional[str] = None,
) -> str:
    """Markdown을 HTML로 변환하고 Mermaid/LaTeX를 처리

    Args:
        md_text: Markdown 텍스트
        title: HTML 문서 제목 (None일 경우 첫 번째 # 헤더 사용)
        use_base64: True면 이미지를 Base64로 인코딩하여 HTML에 임베드
        math_mode: 수식 처리 방식
            - "image" : LaTeX → KaTeX PNG 이미지 (기본)
            - "mathml": LaTeX → MathML HTML 태그 (pandoc이 OMML로 변환)
        md_dir: Markdown 파일이 있는 디렉터리 (상대경로 이미지 기준). None이면 CWD 사용

    Returns:
        완성된 HTML 문자열
    """
    if title is None:
        h1_match = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
        title = h1_match.group(1).strip() if h1_match else "Untitled"

    base_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.join(base_dir, "..")

    mermaid_dir = os.path.join(parent_dir, "mermaid_diagrams")
    md_text = replace_mermaid_with_images(md_text, mermaid_dir, use_base64)

    latex_dir = os.path.join(parent_dir, "latex_equations")
    if math_mode == "mathml":
        md_text = replace_latex_with_mathml(md_text)
    else:
        md_text = replace_latex_with_images(md_text, latex_dir, use_base64)

    md_text = normalize_markdown_spacing(md_text)

    extensions = ["fenced_code", "tables"]
    html_body = markdown.markdown(md_text, extensions=extensions, output_format="html")

    if use_base64 and md_dir:
        from helper_md_doc.helper_html_doc import embed_images_as_base64
        html_body = embed_images_as_base64(html_body, md_dir)
    html_body = re.sub(
        r"(<pre><code[^>]*>)(.*?)(</code></pre>)",
        lambda match: f"{match.group(1)}{html.unescape(match.group(2)).replace('<', '&lt;').replace('>', '&gt;')}{match.group(3)}",
        html_body,
        flags=re.DOTALL,
    )

    scripts = ""
    return HTML_TEMPLATE.format(title=title, scripts=scripts, content=html_body)


def main():
    parser = argparse.ArgumentParser(
        description="Markdown(.md)을 HTML로 변환하고 Mermaid/LaTeX 수식을 처리합니다."
    )
    parser.add_argument("input", help="입력 Markdown 파일 경로 (.md)")
    parser.add_argument("-o", "--output", help="출력 HTML 파일 경로 (.html)")
    parser.add_argument("--title", default=None, help="HTML 문서 제목")
    parser.add_argument(
        "--base64", action="store_true", help="PNG 이미지를 Base64로 인코딩하여 HTML에 임베드"
    )
    parser.add_argument(
        "--math-mode",
        choices=["image", "mathml"],
        default="image",
        help="수식 처리 방식: image=KaTeX PNG(기본), mathml=MathML 태그",
    )
    args = parser.parse_args()

    in_path = args.input
    if not os.path.isfile(in_path):
        logging.warning(f"파일을 찾을 수 없습니다: {in_path}")
        sys.exit(1)

    with open(in_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    title = args.title or os.path.splitext(os.path.basename(in_path))[0]
    result_html = md_to_html(md_text, title=title, use_base64=args.base64, math_mode=args.math_mode)

    out_path = args.output or os.path.splitext(in_path)[0] + ".html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result_html)

    _cleanup_browser()
    logging.info(f"생성 완료: {out_path}")


if __name__ == "__main__":
    main()
