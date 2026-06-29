#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DOCX 사후 처리: 표 스타일/테두리 교정, overline OMML 교정"""

import io
import logging
import re
import zipfile
from typing import Optional

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


# 0.05 cm = 28 twips (1 cm = 566.93 twips)
_KIPS_CELL_MARGIN_TWIPS = "28"
_KIPS_TABLE_CELL_MAR_XML = (
    "<w:tblCellMar>"
    f'<w:top    w:w="{_KIPS_CELL_MARGIN_TWIPS}" w:type="dxa"/>'
    f'<w:left   w:w="{_KIPS_CELL_MARGIN_TWIPS}" w:type="dxa"/>'
    f'<w:bottom w:w="{_KIPS_CELL_MARGIN_TWIPS}" w:type="dxa"/>'
    f'<w:right  w:w="{_KIPS_CELL_MARGIN_TWIPS}" w:type="dxa"/>'
    "</w:tblCellMar>"
)


def fix_tables_in_docx(
    docx_path: str, kips: bool = False, table_font_size: Optional[int] = None
) -> None:
    """DOCX 내 모든 표에 TableGrid 스타일·실선 테두리·가운데 정렬을 직접 적용.

    Args:
        docx_path: 수정할 DOCX 파일 경로 (인플레이스 덮어씀)
        kips: True이면 KIPS 논문 스타일(셀 여백 0.05cm) 추가 적용
        table_font_size: 셀 내 텍스트 폰트 크기(pt). None이면 변경하지 않음
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
        if kips:
            if "w:tblCellMar" in tblpr:
                tblpr = re.sub(
                    r"<w:tblCellMar>.*?</w:tblCellMar>",
                    _KIPS_TABLE_CELL_MAR_XML,
                    tblpr,
                    flags=re.DOTALL,
                )
            else:
                tblpr = tblpr.replace("</w:tblPr>", _KIPS_TABLE_CELL_MAR_XML + "</w:tblPr>")
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
            # "In Table" 단락 스타일 적용
            if "w:pStyle" not in ppr:
                ppr = ppr.replace("<w:pPr>", '<w:pPr><w:pStyle w:val="InTable"/>')
            else:
                # Pandoc은 self-closing 태그에 공백을 넣음: w:val="Compact" />
                ppr = re.sub(r'<w:pStyle\s[^/]*/\s*>',
                             '<w:pStyle w:val="InTable"/>', ppr)
            if "w:jc" not in ppr:
                ppr = ppr.replace("</w:pPr>", '<w:jc w:val="center"/></w:pPr>')
            else:
                ppr = re.sub(r"<w:jc[^/]*/>", '<w:jc w:val="center"/>', ppr)
            return ppr

        def fix_p_no_ppr(pm: re.Match) -> str:
            """<w:pPr>가 없는 <w:p>에 In Table 스타일 + 가운데 정렬 삽입."""
            p = pm.group(0)
            p = p.replace(
                "<w:p>",
                '<w:p><w:pPr><w:pStyle w:val="InTable"/>'
                '<w:jc w:val="center"/></w:pPr>',
                1,
            )
            return p

        # <w:pPr>가 있는 단락: 스타일·정렬 수정
        tc = re.sub(r"<w:pPr>.*?</w:pPr>", fix_ppr, tc, flags=re.DOTALL)
        # <w:pPr>가 없는 <w:p>: 새로 삽입
        tc = re.sub(
            r"<w:p>(?!.*?<w:pPr>.*?</w:pPr>)",
            fix_p_no_ppr,
            tc,
            flags=re.DOTALL,
        )

        if table_font_size is not None:
            sz_val = str(table_font_size * 2)  # pt → half-points (OOXML 단위)

            def fix_run_sz(rm: re.Match) -> str:
                run = rm.group(0)
                if "<w:rPr>" in run:
                    def inject_sz(rpm: re.Match) -> str:
                        rpr = rpm.group(0)
                        if "<w:sz " not in rpr:
                            rpr = rpr.replace(
                                "</w:rPr>",
                                f'<w:sz w:val="{sz_val}"/><w:szCs w:val="{sz_val}"/></w:rPr>',
                            )
                        return rpr
                    run = re.sub(r"<w:rPr>.*?</w:rPr>", inject_sz, run, flags=re.DOTALL)
                else:
                    run = run.replace(
                        "<w:r>",
                        f'<w:r><w:rPr><w:sz w:val="{sz_val}"/><w:szCs w:val="{sz_val}"/></w:rPr>',
                        1,
                    )
                return run

            tc = re.sub(r"<w:r>.*?</w:r>", fix_run_sz, tc, flags=re.DOTALL)

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
