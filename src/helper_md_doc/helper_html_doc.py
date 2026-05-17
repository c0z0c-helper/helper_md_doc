#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pypandoc
import importlib.util
import argparse
import base64
import io
import os
import re
import sys
import zipfile
import logging
from pathlib import Path
from typing import Optional

# 패키지 루트를 sys.path에 추가하여 절대 임포트 통일
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# 의존성 확인 및 설치

spec = importlib.util.spec_from_file_location(
    "requirements_rnac", os.path.join(
        os.path.dirname(__file__), "requirements_rnac.py")
)
requirements_rnac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(requirements_rnac)
requirements_rnac.check_and_install_dependencies()


logging.basicConfig(level=logging.INFO, format="%(message)s")


def embed_images_as_base64(html_text: str, base_dir: Optional[str] = None) -> str:
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
            full_path = os.path.join(base_dir or "", img_path)

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
    Pandoc 변환을 위해 HTML 정리: KaTeX 스크립트/링크 제거 및 코드블록 래핑.

    <pre><code> 블록을 custom-style="Code Fence" Div로 래핑하여
    DOCX 변환 시 Code Fence 스타일(테두리 박스)이 적용되도록 합니다.

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
    html_text = re.sub(r"<link[^>]*katex[^>]*>", "",
                       html_text, flags=re.IGNORECASE)
    html_text = re.sub(
        r"<script[^>]*katex[^>]*>.*?</script>", "", html_text, flags=re.IGNORECASE | re.DOTALL
    )
    html_text = re.sub(
        r"<script[^>]*mermaid[^>]*>.*?</script>", "", html_text, flags=re.IGNORECASE | re.DOTALL
    )

    # <pre><code ...>...</code></pre> 블록을 custom-style="Code Fence" Div로 래핑
    # pandoc은 <pre> 블록을 SourceCode로 처리하므로, 줄별 <p>로 분해하여 래핑해야
    # custom-style 속성이 정상 적용됨
    def wrap_pre_block(match: re.Match) -> str:
        inner = match.group(1)
        # HTML 엔티티 복원 (pandoc이 plain text로 전달받도록)
        inner = (
            inner.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
        )
        # 줄별로 <p> 태그로 감싸기 (빈 줄은 공백 유지)
        lines = inner.split("\n")
        # 마지막 빈 줄 제거
        while lines and not lines[-1].strip():
            lines.pop()

        def preserve_indent(line: str) -> str:
            """선행 공백/탭을 &#160;(NBSP)로 치환하여 DOCX에서 들여쓰기 보존."""
            if not line:
                return "&#160;"
            # 선행 공백 문자(스페이스·탭) 개수 계산 후 NBSP로 치환
            stripped = line.lstrip()
            indent = line[: len(line) - len(stripped)]
            # 탭은 4 NBSP, 스페이스는 1 NBSP로 변환
            nbsp_indent = indent.replace(
                "\t", "&#160;&#160;&#160;&#160;").replace(" ", "&#160;")
            return nbsp_indent + stripped

        p_lines = "".join(f"<p>{preserve_indent(line)}</p>" for line in lines)
        return f'<div custom-style="Code Fence">{p_lines}</div>'

    html_text = re.sub(
        r"<pre><code[^>]*>(.*?)</code></pre>",
        wrap_pre_block,
        html_text,
        flags=re.DOTALL,
    )

    # 블록 수식 div (text-align:center) → custom-style="Image Center"
    # 패턴: <div style="text-align: center; ..."><img ... /></div>
    html_text = re.sub(
        r'<div style="text-align: center;[^"]*">(<img [^>]+/>)</div>',
        r'<div custom-style="Image Center">\1</div>',
        html_text,
    )

    return html_text


# 패키지 내장 reference.docx 경로 (Code Fence 스타일 정의 포함)
_REFERENCE_DOCX = os.path.join(os.path.dirname(__file__), "reference.docx")

# Pandoc MathML→OMML 변환 시 \overline이 <m:limUpp>로 잘못 생성되는 문제 수정.
# 바(bar) 문자(U+00AF ¯)를 상한(limit)으로 사용하는 <m:limUpp>를 <m:bar pos=top>으로 교체.
_BAR_CHARS = {"\u00af", "\u02015", "\u203e", "\u0305"}  # ¯ ‒ ‾ ̅
_RE_LIMUPP_BAR = re.compile(
    r"<m:limUpp>"
    r"(<m:e>(?:(?!<m:e>|</m:e>).)*</m:e>)"   # <m:e>...</m:e> (중첩 없는 단순 캡처)
    r"<m:lim>(?:<m:r>(?:<m:rPr>.*?</m:rPr>)?<m:t>([^<]*)</m:t></m:r>)+</m:lim>"
    r"</m:limUpp>",
    re.DOTALL,
)


def _fix_overline_omml(xml: str) -> str:
    """OMML XML에서 bar 문자를 상한으로 사용하는 <m:limUpp>를 <m:bar pos=top>으로 교체."""

    def replace_limupp(m: re.Match) -> str:
        inner_e = m.group(1)
        # <m:t> 내부 텍스트만 수집
        lim_texts = re.findall(r"<m:t>([^<]*)</m:t>", m.group(0)[m.end(1):])
        combined = "".join(lim_texts).strip()
        if all(ch in _BAR_CHARS for ch in combined) and combined:
            return (
                "<m:bar>"
                "<m:barPr><m:pos m:val=\"top\"/></m:barPr>"
                f"{inner_e}"
                "</m:bar>"
            )
        return m.group(0)

    return _RE_LIMUPP_BAR.sub(replace_limupp, xml)


_TABLE_BORDER_XML = (
    "<w:tblBorders>"
    '<w:top    w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:left   w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:right  w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    "</w:tblBorders>"
)


def fix_tables_in_docx(docx_path: str) -> None:
    """DOCX 내 모든 표에 TableGrid 스타일·실선 테두리·가운데 정렬을 직접 적용.

    pandoc HTML→DOCX 변환 후 word/document.xml을 수정하여:
    - <w:tblPr>: TableGrid 스타일 지정 + 실선 테두리 삽입
    - <w:tcPr>:  수직 가운데 정렬 (vAlign center)
    - <w:pPr> inside <w:tc>: 수평 가운데 정렬 (jc center)

    Args:
        docx_path: 수정할 DOCX 파일 경로 (인플레이스 덮어씀)
    """

    def fix_tblpr(m: re.Match) -> str:
        tblpr = m.group(0)
        # tblStyle 교체 또는 삽입
        if "w:tblStyle" in tblpr:
            tblpr = re.sub(r"<w:tblStyle[^/]*/>",
                           '<w:tblStyle w:val="TableGrid"/>', tblpr)
        else:
            tblpr = tblpr.replace(
                "<w:tblPr>", '<w:tblPr><w:tblStyle w:val="TableGrid"/>')
        # tblBorders 교체 또는 삽입
        if "w:tblBorders" in tblpr:
            tblpr = re.sub(
                r"<w:tblBorders>.*?</w:tblBorders>", _TABLE_BORDER_XML, tblpr, flags=re.DOTALL
            )
        else:
            tblpr = tblpr.replace(
                "</w:tblPr>", _TABLE_BORDER_XML + "</w:tblPr>")
        return tblpr

    def fix_tc(m: re.Match) -> str:
        tc = m.group(0)
        # tcPr 수직 가운데 정렬
        if "<w:tcPr>" in tc:
            if "w:vAlign" not in tc:
                tc = re.sub(
                    r"</w:tcPr>", "<w:vAlign w:val=\"center\"/></w:tcPr>", tc, count=1)
        else:
            tc = tc.replace(
                "<w:tc>", "<w:tc><w:tcPr><w:vAlign w:val=\"center\"/></w:tcPr>", 1)
        # 셀 내 단락 수평 가운데 정렬

        def fix_ppr(pm: re.Match) -> str:
            ppr = pm.group(0)
            if "w:jc" not in ppr:
                ppr = ppr.replace(
                    "</w:pPr>", "<w:jc w:val=\"center\"/></w:pPr>")
            else:
                ppr = re.sub(r"<w:jc[^/]*/>", '<w:jc w:val="center"/>', ppr)
            return ppr
        tc = re.sub(r"<w:pPr>.*?</w:pPr>", fix_ppr, tc, flags=re.DOTALL)
        return tc

    buf = io.BytesIO()
    with zipfile.ZipFile(docx_path, "r") as zin, \
            zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                xml = data.decode("utf-8")
                xml = re.sub(r"<w:tblPr>.*?</w:tblPr>",
                             fix_tblpr, xml, flags=re.DOTALL)
                xml = re.sub(r"<w:tc>.*?</w:tc>", fix_tc, xml, flags=re.DOTALL)
                data = xml.encode("utf-8")
                logging.debug("표 스타일/테두리/정렬 교정 완료")
            zout.writestr(item, data)
    with open(docx_path, "wb") as f:
        f.write(buf.getvalue())


def fix_overline_in_docx(docx_path: str) -> None:
    """DOCX 파일 내 OMML의 잘못된 overline(<m:limUpp>) 표현을 <m:bar>로 수정 (인플레이스).

    Pandoc의 MathML→OMML 변환 시 LaTeX \\overline이 상한기호(<m:limUpp>)로
    잘못 생성되는 문제를 사후 교정합니다.

    Args:
        docx_path: 수정할 DOCX 파일 경로 (덮어씀)
    """
    targets = ("word/document.xml", "word/footnotes.xml", "word/endnotes.xml")
    buf = io.BytesIO()
    with zipfile.ZipFile(docx_path, "r") as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename in targets:
                xml = data.decode("utf-8")
                fixed = _fix_overline_omml(xml)
                if fixed != xml:
                    logging.debug(f"overline 수식 교정: {item.filename}")
                data = fixed.encode("utf-8")
            zout.writestr(item, data)
    with open(docx_path, "wb") as f:
        f.write(buf.getvalue())


def html_to_doc(html_path: str, output_path: str, reference_doc: Optional[str] = None) -> None:
    """
    HTML 파일을 DOCX로 변환 (이미지/수식 임베딩).

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
