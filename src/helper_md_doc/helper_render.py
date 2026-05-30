#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Playwright 브라우저 관리 및 Mermaid/LaTeX 렌더링"""

from playwright.sync_api import sync_playwright, Browser, Page
from PIL import Image, ImageChops
import base64
import io
import json
import logging
import os
import re
from typing import Optional, Tuple, List

logging.basicConfig(level=logging.INFO, format="%(message)s")

# 전역 Playwright 브라우저 (다이어그램 렌더링 성능 최적화)
_playwright = None
_browser: Optional[Browser] = None
_page: Optional[Page] = None


def _get_browser_page() -> Page:
    """Playwright 브라우저 페이지를 전역 캐싱으로 반환 (성능 최적화)"""
    global _playwright, _browser, _page
    if _page is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=True)
        _page = _browser.new_page()

        mermaid_js_path = os.path.join(os.path.dirname(__file__), "mermaid/mermaid.js")
        with open(mermaid_js_path, "r", encoding="utf-8") as f:
            mermaid_js = f.read()
        _page.add_script_tag(content=mermaid_js)
        _page.evaluate("mermaid.initialize({ startOnLoad: false, theme: 'default' })")

        katex_js_path = os.path.join(os.path.dirname(__file__), "katex", "katex.js")
        katex_css_path = os.path.join(os.path.dirname(__file__), "katex", "katex.css")
        with open(katex_js_path, "r", encoding="utf-8") as f:
            katex_js = f.read()
        with open(katex_css_path, "r", encoding="utf-8") as f:
            katex_css = f.read()
        _page.add_script_tag(content=katex_js)
        _page.add_style_tag(content=katex_css)
    return _page


def _cleanup_browser() -> None:
    """브라우저 리소스 정리"""
    global _playwright, _browser, _page
    if _page:
        _page.close()
    if _browser:
        _browser.close()
    if _playwright:
        _playwright.stop()
    _page = _browser = _playwright = None


def sanitize_mermaid_code(mermaid_code: str) -> str:
    """Mermaid 코드의 노드 라벨 내 HTML/Markdown 특수문자를 전각문자로 변환하여 파싱 오류 방지

    Args:
        mermaid_code: 원본 Mermaid 다이어그램 코드

    Returns:
        노드 라벨 내 특수문자가 전각문자로 변환된 Mermaid 코드
    """
    special_chars = {
        "<": "＜",
        ">": "＞",
        "&": "＆",
        "_": "＿",
    }

    def replace_in_label(match):
        label_content = match.group(1)
        label_content = label_content.replace("<br/>", "\x00PLACEHOLDER\x01BR\x01SLASH\x00")
        label_content = label_content.replace("<br>", "\x00PLACEHOLDER\x01BR\x00")
        for ascii_char, fullwidth_char in special_chars.items():
            label_content = label_content.replace(ascii_char, fullwidth_char)
        label_content = label_content.replace("\x00PLACEHOLDER\x01BR\x01SLASH\x00", "<br/>")
        label_content = label_content.replace("\x00PLACEHOLDER\x01BR\x00", "<br>")
        return f'["{label_content}"]'

    return re.sub(r'\["([^"]+)"\]', replace_in_label, mermaid_code)


def _crop_whitespace(
    png_bytes: bytes, padding: int = 2, tolerance: int = 10, dpi: int = 0
) -> bytes:
    """PNG bytes에서 가장자리 픽셀 기반으로 배경색을 자동 감지하여 여백을 제거

    Args:
        png_bytes: 원본 PNG 바이너리 데이터
        padding: crop 후 사방에 남길 여백 픽셀 수
        tolerance: 배경색으로 판단할 색상 허용 오차 (0~255)
        dpi: PNG 메타데이터에 삽입할 DPI 값 (0이면 미설정)

    Returns:
        여백이 제거된 PNG 바이너리 데이터
    """
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    bg.paste(img, mask=img.split()[3])
    rgb = bg.convert("RGB")

    w, h = rgb.size
    corner_size = min(3, w, h)
    sample_pixels: List[Tuple[int, int, int]] = []
    regions = [
        (0, 0, corner_size, corner_size),
        (w - corner_size, 0, w, corner_size),
        (0, h - corner_size, corner_size, h),
        (w - corner_size, h - corner_size, w, h),
    ]
    for region in regions:
        patch = rgb.crop(region)
        sample_pixels.extend(tuple(patch.getdata()))  # type: ignore[arg-type]

    r_avg = sum(p[0] for p in sample_pixels) // len(sample_pixels)
    g_avg = sum(p[1] for p in sample_pixels) // len(sample_pixels)
    b_avg = sum(p[2] for p in sample_pixels) // len(sample_pixels)
    bg_color = (r_avg, g_avg, b_avg)

    bg_image = Image.new("RGB", rgb.size, bg_color)
    diff = ImageChops.difference(rgb, bg_image)
    lut = [0 if v <= tolerance else v for v in range(256)]
    diff = diff.point(lut * 3)
    bbox = diff.getbbox()
    if bbox is None:
        return png_bytes

    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(w, bbox[2] + padding)
    bottom = min(h, bbox[3] + padding)

    cropped = rgb.crop((left, top, right, bottom))
    buf = io.BytesIO()
    save_kwargs: dict = {"format": "PNG"}
    if dpi > 0:
        save_kwargs["dpi"] = (dpi, dpi)
    cropped.save(buf, **save_kwargs)
    return buf.getvalue()


def png_to_base64(png_path: str) -> str:
    """PNG 파일을 Base64 문자열로 인코딩

    Args:
        png_path: PNG 파일 경로

    Returns:
        data:image/png;base64,... 형식의 Base64 문자열
    """
    with open(png_path, "rb") as f:
        png_data = f.read()
    b64_data = base64.b64encode(png_data).decode("utf-8")
    return f"data:image/png;base64,{b64_data}"


def render_mermaid_to_png(mermaid_code: str, output_path: str) -> str:
    """Playwright로 Mermaid 다이어그램을 PNG로 렌더링 (최적화: 브라우저 재사용)

    Args:
        mermaid_code: Mermaid 다이어그램 코드
        output_path: PNG 파일 저장 경로

    Returns:
        PNG 파일 경로
    """
    mermaid_code = sanitize_mermaid_code(mermaid_code)
    page = _get_browser_page()

    html_content = f"""
    <div id="mermaid-container" style="background: white; padding: 20px;">
        <div class="mermaid">{mermaid_code}</div>
    </div>
    """
    page.set_content(f"<!DOCTYPE html><html><body>{html_content}</body></html>")
    page.evaluate("void mermaid.run({ querySelector: '.mermaid' })")
    page.wait_for_selector(".mermaid svg", timeout=5000)

    svg_element = page.query_selector(".mermaid svg")
    if svg_element:
        png_bytes = svg_element.screenshot()
        png_bytes = _crop_whitespace(png_bytes)
        with open(output_path, "wb") as f:
            f.write(png_bytes)

    return output_path


def render_mermaid_base64(mermaid_code: str) -> str:
    """Playwright로 Mermaid 다이어그램을 Base64 Data URL로 변환 (파일 저장 없음)

    Args:
        mermaid_code: Mermaid 다이어그램 코드

    Returns:
        data:image/png;base64,... 형식의 Base64 문자열
    """
    mermaid_code = sanitize_mermaid_code(mermaid_code)
    page = _get_browser_page()

    html_content = f"""
    <div id="mermaid-container" style="background: white; padding: 20px;">
        <div class="mermaid">{mermaid_code}</div>
    </div>
    """
    page.set_content(f"<!DOCTYPE html><html><body>{html_content}</body></html>")
    page.evaluate("void mermaid.run({ querySelector: '.mermaid' })")
    page.wait_for_selector(".mermaid svg", timeout=5000)

    svg_element = page.query_selector(".mermaid svg")
    if svg_element:
        png_bytes = svg_element.screenshot()
        png_bytes = _crop_whitespace(png_bytes)
        b64_data = base64.b64encode(png_bytes).decode("utf-8")
        return f"data:image/png;base64,{b64_data}"

    return ""


def render_latex_to_png(latex_code: str, output_path: str, display_mode: bool = False) -> str:
    """Playwright로 KaTeX 수식을 PNG로 렌더링

    Args:
        latex_code: LaTeX 수식 코드 ($ 기호 제외)
        output_path: PNG 파일 저장 경로
        display_mode: True면 블록 수식, False면 인라인 수식

    Returns:
        PNG 파일 경로
    """
    global _playwright, _browser
    if _browser is None:
        if _playwright is None:
            _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=True)

    page = _browser.new_page()

    try:
        latex_json = json.dumps(latex_code)
        container_style = "background: white; padding: 10px; display: inline-block;"

        katex_css_path = os.path.join(os.path.dirname(__file__), "katex", "katex.css")
        with open(katex_css_path, "r", encoding="utf-8") as f:
            katex_css = f.read()

        katex_js_path = os.path.join(os.path.dirname(__file__), "katex", "katex.js")
        with open(katex_js_path, "r", encoding="utf-8") as f:
            katex_js = f.read()

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>{katex_css}</style>
</head>
<body>
    <div id="latex-container" style="{container_style}">
        <span id="latex-output"></span>
    </div>
    <script>{katex_js}</script>
    <script>
        const latex = {latex_json};
        const outputElement = document.getElementById('latex-output');
        try {{
            katex.render(latex, outputElement, {{
                displayMode: {str(display_mode).lower()},
                throwOnError: false
            }});
        }} catch (e) {{
            console.error('KaTeX error:', e);
            outputElement.textContent = 'Error rendering equation';
        }}
    </script>
</body>
</html>"""
        page.set_content(html_content)
        page.wait_for_load_state("networkidle")

        latex_element = page.query_selector("#latex-container")
        if latex_element:
            png_bytes = latex_element.screenshot()
            png_bytes = _crop_whitespace(png_bytes, dpi=150)
            with open(output_path, "wb") as f:
                f.write(png_bytes)
        else:
            logging.warning(f"LaTeX 렌더링 실패: {latex_code[:50]}...")
    finally:
        page.close()

    return output_path


def render_latex_base64(latex_code: str, display_mode: bool = False) -> str:
    """Playwright로 KaTeX 수식을 Base64 Data URL로 변환 (파일 저장 없음)

    Args:
        latex_code: LaTeX 수식 코드 ($ 기호 제외)
        display_mode: True면 블록 수식, False면 인라인 수식

    Returns:
        data:image/png;base64,... 형식의 Base64 문자열
    """
    global _playwright, _browser
    if _browser is None:
        if _playwright is None:
            _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=True)

    page = _browser.new_page()

    try:
        latex_json = json.dumps(latex_code)
        container_style = "background: white; padding: 10px; display: inline-block;"

        katex_css_path = os.path.join(os.path.dirname(__file__), "katex", "katex.css")
        with open(katex_css_path, "r", encoding="utf-8") as f:
            katex_css = f.read()

        katex_js_path = os.path.join(os.path.dirname(__file__), "katex", "katex.js")
        with open(katex_js_path, "r", encoding="utf-8") as f:
            katex_js = f.read()

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>{katex_css}</style>
</head>
<body>
    <div id="latex-container" style="{container_style}">
        <span id="latex-output"></span>
    </div>
    <script>{katex_js}</script>
    <script>
        const latex = {latex_json};
        const outputElement = document.getElementById('latex-output');
        try {{
            katex.render(latex, outputElement, {{
                displayMode: {str(display_mode).lower()},
                throwOnError: false
            }});
        }} catch (e) {{
            console.error('KaTeX error:', e);
            outputElement.textContent = 'Error rendering equation';
        }}
    </script>
</body>
</html>"""
        page.set_content(html_content)
        page.wait_for_load_state("networkidle")

        latex_element = page.query_selector("#latex-container")
        if latex_element:
            png_bytes = latex_element.screenshot()
            png_bytes = _crop_whitespace(png_bytes, dpi=150)
            b64_data = base64.b64encode(png_bytes).decode("utf-8")
            return f"data:image/png;base64,{b64_data}"
        else:
            logging.warning(f"LaTeX 렌더링 실패: {latex_code[:50]}...")
            return ""
    finally:
        page.close()
