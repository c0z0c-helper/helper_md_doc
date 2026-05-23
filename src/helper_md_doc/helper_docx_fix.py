#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DOCX 사후 처리: 표 스타일/테두리 교정, overline OMML 교정"""

import io
import logging
import re
import zipfile

logging.basicConfig(level=logging.INFO, format="%(message)s")

# Pandoc MathML→OMML 변환 시 \overline이 <m:limUpp>로 잘못 생성되는 문제 수정.
_BAR_CHARS = {"\u00af", "\u02015", "\u203e", "\u0305"}  # ¯ ‒ ‾ ̅
_RE_LIMUPP_BAR = re.compile(
    r"<m:limUpp>"
    r"(<m:e>(?:(?!<m:e>|</m:e>).)*</m:e>)"
    r"<m:lim>(?:<m:r>(?:<m:rPr>.*?</m:rPr>)?<m:t>([^<]*)</m:t></m:r>)+</m:lim>"
    r"</m:limUpp>",
    re.DOTALL,
)

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


def _fix_overline_omml(xml: str) -> str:
    """OMML XML에서 bar 문자를 상한으로 사용하는 <m:limUpp>를 <m:bar pos=top>으로 교체."""

    def replace_limupp(m: re.Match) -> str:
        inner_e = m.group(1)
        lim_texts = re.findall(r"<m:t>([^<]*)</m:t>", m.group(0)[m.end(1):])
        combined = "".join(lim_texts).strip()
        if all(ch in _BAR_CHARS for ch in combined) and combined:
            return (
                "<m:bar>"
                '<m:barPr><m:pos m:val="top"/></m:barPr>'
                f"{inner_e}"
                "</m:bar>"
            )
        return m.group(0)

    return _RE_LIMUPP_BAR.sub(replace_limupp, xml)


def fix_tables_in_docx(docx_path: str) -> None:
    """DOCX 내 모든 표에 TableGrid 스타일·실선 테두리·가운데 정렬을 직접 적용.

    Args:
        docx_path: 수정할 DOCX 파일 경로 (인플레이스 덮어씀)
    """

    def fix_tblpr(m: re.Match) -> str:
        tblpr = m.group(0)
        if "w:tblStyle" in tblpr:
            tblpr = re.sub(r"<w:tblStyle[^/]*/>",
                           '<w:tblStyle w:val="TableGrid"/>', tblpr)
        else:
            tblpr = tblpr.replace(
                "<w:tblPr>", '<w:tblPr><w:tblStyle w:val="TableGrid"/>')
        if "w:tblBorders" in tblpr:
            tblpr = re.sub(
                r"<w:tblBorders>.*?</w:tblBorders>", _TABLE_BORDER_XML, tblpr, flags=re.DOTALL
            )
        else:
            tblpr = tblpr.replace("</w:tblPr>", _TABLE_BORDER_XML + "</w:tblPr>")
        return tblpr

    def fix_tc(m: re.Match) -> str:
        tc = m.group(0)
        if "<w:tcPr>" in tc:
            if "w:vAlign" not in tc:
                tc = re.sub(
                    r"</w:tcPr>", '<w:vAlign w:val="center"/></w:tcPr>', tc, count=1)
        else:
            tc = tc.replace(
                "<w:tc>", '<w:tc><w:tcPr><w:vAlign w:val="center"/></w:tcPr>', 1)

        def fix_ppr(pm: re.Match) -> str:
            ppr = pm.group(0)
            if "w:jc" not in ppr:
                ppr = ppr.replace("</w:pPr>", '<w:jc w:val="center"/></w:pPr>')
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

    Args:
        docx_path: 수정할 DOCX 파일 경로 (덮어씀)
    """
    targets = ("word/document.xml", "word/footnotes.xml", "word/endnotes.xml")
    buf = io.BytesIO()
    with zipfile.ZipFile(docx_path, "r") as zin, \
            zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
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
