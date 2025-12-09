#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import base64
import os
import re
import sys
import logging
import markdown
from playwright.sync_api import sync_playwright, Browser, Page
from typing import Optional, Tuple, List

logging.basicConfig(level=logging.INFO, format='%(message)s')
# body {{{{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", Arial, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; line-height: 1.6; padding: 2rem; max-width: 900px; margin: auto; }}}}
# pre {{{{ background: #f6f8fa; padding: 1rem; overflow: auto; border-radius: 6px; }}}}
# code {{{{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; font-size: 8px; }}}}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <style>
    body {{{{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", Arial, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; line-height: 1.6; padding: 2rem; max-width: 900px; margin: auto; }}}}
    pre {{{{ background: #f6f8fa; padding: 1rem; overflow: auto; border-radius: 6px; }}}}
    code {{{{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; font-size: 8px; }}}}
    table {{{{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}}}
    th, td {{{{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}}}
    th {{{{ background: #f6f8fa; font-weight: 600; }}}}
    .mermaid {{{{ margin: 1rem 0; }}}}
  </style>
  {scripts}
</head>
<body>
{content}
</body>
</html>
"""

# 전역 Playwright 브라우저 (다이어그램 렌더링 성능 최적화)
_playwright = None
_browser: Optional[Browser] = None
_page: Optional[Page] = None

def _get_browser_page():
    """Playwright 브라우저 페이지를 전역 캐싱으로 반환 (성능 최적화)"""
    global _playwright, _browser, _page
    if _page is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=True)
        _page = _browser.new_page()
        
        # mermaid.min.js 사전 로드
        mermaid_js_path = os.path.join(os.path.dirname(__file__), "mermaid/mermaid.js")
        with open(mermaid_js_path, "r", encoding="utf-8") as f:
            mermaid_js = f.read()
        _page.add_script_tag(content=mermaid_js)
        _page.evaluate("mermaid.initialize({ startOnLoad: false, theme: 'default' })")
        
        # katex.min.js 및 CSS 사전 로드
        katex_js_path = os.path.join(os.path.dirname(__file__), "katex", "katex.js")
        katex_css_path = os.path.join(os.path.dirname(__file__), "katex", "katex.css")
        with open(katex_js_path, "r", encoding="utf-8") as f:
            katex_js = f.read()
        with open(katex_css_path, "r", encoding="utf-8") as f:
            katex_css = f.read()
        _page.add_script_tag(content=katex_js)
        _page.add_style_tag(content=katex_css)
    return _page

def _cleanup_browser():
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
    # HTML/Markdown 파싱 오류를 일으키는 특수문자 매핑 (ASCII → 전각문자)
    special_chars = {
        '<': '＜',   # U+FF1C FULLWIDTH LESS-THAN SIGN
        '>': '＞',   # U+FF1E FULLWIDTH GREATER-THAN SIGN
        '&': '＆',   # U+FF06 FULLWIDTH AMPERSAND
        '_': '＿',   # U+FF3F FULLWIDTH LOW LINE (언더바)
    }
    
    def replace_in_label(match):
        """노드 라벨 내부의 특수문자만 전각문자로 변환 (<br/>, <br> 제외)"""
        label_content = match.group(1)
        
        # <br/> 및 <br> 태그를 임시 플레이스홀더로 치환 (줄바꿈 태그 보존)
        # 주의: special_chars에 '_'가 있으므로 언더바를 사용하지 않는 플레이스홀더 사용
        label_content = label_content.replace('<br/>', '\x00PLACEHOLDER\x01BR\x01SLASH\x00')
        label_content = label_content.replace('<br>', '\x00PLACEHOLDER\x01BR\x00')
        
        # 특수문자 변환
        for ascii_char, fullwidth_char in special_chars.items():
            label_content = label_content.replace(ascii_char, fullwidth_char)
        
        # 플레이스홀더 복원
        label_content = label_content.replace('\x00PLACEHOLDER\x01BR\x01SLASH\x00', '<br/>')
        label_content = label_content.replace('\x00PLACEHOLDER\x01BR\x00', '<br>')
        
        return f'["{label_content}"]'
    
    # 패턴: ["..."] 형태의 노드 라벨 찾기
    mermaid_code = re.sub(r'\["([^"]+)"\]', replace_in_label, mermaid_code)
    
    return mermaid_code

def png_to_base64(png_path: str) -> str:
    """PNG 파일을 Base64 문자열로 인코딩
    
    Args:
        png_path: PNG 파일 경로
        
    Returns:
        data:image/png;base64,... 형식의 Base64 문자열
    """
    with open(png_path, "rb") as f:
        png_data = f.read()
    b64_data = base64.b64encode(png_data).decode('utf-8')
    return f"data:image/png;base64,{b64_data}"

def render_mermaid_to_png(mermaid_code: str, output_path: str) -> str:
    """Playwright로 Mermaid 다이어그램을 PNG로 렌더링 (최적화: 브라우저 재사용)
    
    Args:
        mermaid_code: Mermaid 다이어그램 코드
        output_path: PNG 파일 저장 경로
        
    Returns:
        PNG 파일 경로
    """
    # HTML 특수문자 전처리 (파싱 오류 방지)
    mermaid_code = sanitize_mermaid_code(mermaid_code)
    
    page = _get_browser_page()
    
    # HTML 컨테이너 생성 및 Mermaid 렌더링
    html_content = f"""
    <div id="mermaid-container" style="background: white; padding: 20px;">
        <div class="mermaid">{mermaid_code}</div>
    </div>
    """
    page.set_content(f"<!DOCTYPE html><html><body>{html_content}</body></html>")
    # page.evaluate("""async () => {
    #     await mermaid.run({ querySelector: '.mermaid' });
    # }""")
    page.evaluate("void mermaid.run({ querySelector: '.mermaid' })")
    page.wait_for_selector('.mermaid svg', timeout=5000)
    
    # SVG 요소 스크린샷
    svg_element = page.query_selector('.mermaid svg')
    if svg_element:
        svg_element.screenshot(path=output_path)
    
    return output_path

def render_mermaid_base64(mermaid_code: str) -> str:
    """Playwright로 Mermaid 다이어그램을 Base64 Data URL로 변환 (파일 저장 없음)
    
    Args:
        mermaid_code: Mermaid 다이어그램 코드
        
    Returns:
        data:image/png;base64,... 형식의 Base64 문자열
    """
    # HTML 특수문자 전처리 (파싱 오류 방지)
    mermaid_code = sanitize_mermaid_code(mermaid_code)
    
    page = _get_browser_page()
    
    html_content = f"""
    <div id="mermaid-container" style="background: white; padding: 20px;">
        <div class="mermaid">{mermaid_code}</div>
    </div>
    """
    page.set_content(f"<!DOCTYPE html><html><body>{html_content}</body></html>")
    # page.evaluate("""async () => {
    #     await mermaid.run({ querySelector: '.mermaid' });
    # }""")
    page.evaluate("void mermaid.run({ querySelector: '.mermaid' })")
    page.wait_for_selector('.mermaid svg', timeout=5000)
    
    svg_element = page.query_selector('.mermaid svg')
    if svg_element:
        png_bytes = svg_element.screenshot()
        b64_data = base64.b64encode(png_bytes).decode('utf-8')
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
    # 새 페이지 생성 (이전 상태 영향 방지)
    global _playwright, _browser
    if _browser is None:
        if _playwright is None:
            _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=True)
    
    page = _browser.new_page()
    
    try:
        # LaTeX 코드의 백슬래시 이스케이프 처리 (JSON 문자열로 전달하기 위해)
        import json
        latex_json = json.dumps(latex_code)
        
        # HTML 컨테이너 생성
        container_style = "background: white; padding: 10px; display: inline-block;"
        
        # KaTeX CSS 읽기
        katex_css_path = os.path.join(os.path.dirname(__file__), "katex", "katex.css")
        with open(katex_css_path, "r", encoding="utf-8") as f:
            katex_css = f.read()
        
        # KaTeX JS 읽기
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
        page.wait_for_load_state('networkidle')
        
        # 렌더링된 요소 스크린샷 (흰색 배경)
        latex_element = page.query_selector('#latex-container')
        if latex_element:
            latex_element.screenshot(path=output_path)
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
        import json
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
        page.wait_for_load_state('networkidle')
        
        latex_element = page.query_selector('#latex-container')
        if latex_element:
            png_bytes = latex_element.screenshot()
            b64_data = base64.b64encode(png_bytes).decode('utf-8')
            return f"data:image/png;base64,{b64_data}"
        else:
            logging.warning(f"LaTeX 렌더링 실패: {latex_code[:50]}...")
            return ""
    finally:
        page.close()

def replace_mermaid_with_images(md_text: str, output_dir: str = "mermaid_diagrams", use_base64: bool = False) -> str:
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
    
    pattern = r'```mermaid\n(.*?)```'
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

def is_simple_text(text: str) -> bool:
    """LaTeX 명령어가 없는 단순 텍스트인지 판별
    
    Args:
        text: 검사할 텍스트
        
    Returns:
        True면 단순 텍스트, False면 LaTeX 수식
    """
    # LaTeX 명령어 패턴: \command, {}, ^, _, 등
    latex_patterns = [r'\\[a-zA-Z]+', r'[_^{}]', r'\\[^a-zA-Z]']
    for pattern in latex_patterns:
        if re.search(pattern, text):
            return False
    return True

def replace_latex_with_images(md_text: str, output_dir: str = "latex_equations", use_base64: bool = False) -> str:
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
        """블록 수식 $$...$$ 치환"""
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
        """인라인 수식 $...$ 치환"""
        latex_code = match.group(1).strip()
        
        if is_simple_text(latex_code):
            return f'<code>{latex_code}</code>'
        
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
    
    md_text = re.sub(r'\$\$(.*?)\$\$', replace_display_math, md_text, flags=re.DOTALL)
    md_text = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', replace_inline_math, md_text)
    
    return md_text

def is_list_or_special_line(line: str) -> bool:
    """라인이 리스트 항목이나 특수 패턴으로 시작하는지 확인
    
    Args:
        line: 검사할 라인
        
    Returns:
        True면 리스트/특수 라인, False면 일반 텍스트
    """
    stripped = line.lstrip()
    # 순서 없는 리스트: -, *, +
    if stripped.startswith(('- ', '* ', '+ ')):
        return True
    # 순서 있는 리스트: 1., 2., 등
    if re.match(r'^\d+\.\s', stripped):
        return True
    # 해시태그: #
    if stripped.startswith('#'):
        return True
    return False

def normalize_markdown_spacing(md_text: str) -> str:
    """Markdown 리스트 앞에 빈 줄 추가 및 이스케이프된 볼드 마커 복원 (python-markdown 호환성)
    
    리스트나 특수 라인들 사이에 빈 줄이 없으면 <br/> 태그를 추가하여 
    HTML 렌더링 시 줄바꿈이 표시되도록 합니다.
    """
    # BOM(Byte Order Mark) 제거: UTF-8 BOM(\ufeff)이 파일 앞에 있으면 Markdown 파싱 실패
    if md_text and md_text[0] == '\ufeff':
        md_text = md_text[1:]
    
    # 이스케이프된 볼드 마커 제거: \*\*text\*\* → **text**
    # 패턴: 백슬래시로 이스케이프된 별표 쌍만 변환
    md_text = re.sub(r'\\\*\\\*([^*]+?)\\\*\\\*', r'**\1**', md_text)
    
    # 리스트 항목 사이에 <br/> 추가 (빈 줄이 없는 경우만)
    lines = md_text.split('\n')
    result_lines = []
    
    for i, line in enumerate(lines):
        result_lines.append(line)
        
        # 마지막 라인이 아니고, 현재 라인이 비어있지 않은 경우
        if i < len(lines) - 1 and line.strip():
            next_line = lines[i + 1]
            
            # 다음 라인이 비어있으면 이미 구분되어 있으므로 <br/> 추가 안함
            if not next_line.strip():
                continue
            
            # 다음 라인이 리스트나 특수 라인으로 시작하는 경우
            # 현재 라인도 콘텐츠가 있으면 <br/> 추가
            if is_list_or_special_line(next_line):
                result_lines.append('<br/>')
    
    return '\n'.join(result_lines)

def md_to_html(
    md_text: str, 
    title: Optional[str] = None,
    use_base64: bool = False
) -> str:
    """Markdown을 HTML로 변환하고 Mermaid/LaTeX를 PNG 이미지로 렌더링
    
    Args:
        md_text: Markdown 텍스트
        title: HTML 문서 제목 (None일 경우 첫 번째 # 헤더 사용)
        use_base64: True면 이미지를 Base64로 인코딩하여 HTML에 임베드
        
    Returns:
        완성된 HTML 문자열
    """
    if title is None:
        h1_match = re.search(r'^#\s+(.+)$', md_text, re.MULTILINE)
        title = h1_match.group(1).strip() if h1_match else "Document"
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.join(base_dir, "..")
    
    # Mermaid 다이어그램을 이미지로 변환
    mermaid_dir = os.path.join(parent_dir, "mermaid_diagrams")
    md_text = replace_mermaid_with_images(md_text, mermaid_dir, use_base64)
    
    # LaTeX 수식을 이미지로 변환
    latex_dir = os.path.join(parent_dir, "latex_equations")
    md_text = replace_latex_with_images(md_text, latex_dir, use_base64)
    
    # Markdown 리스트 정규화
    md_text = normalize_markdown_spacing(md_text)
    
    extensions = ["fenced_code", "tables", "toc"]
    html_body = markdown.markdown(md_text, extensions=extensions, output_format="html")
    
    scripts = ""
    
    return HTML_TEMPLATE.format(title=title, scripts=scripts, content=html_body)

def main():
    parser = argparse.ArgumentParser(
        description="Markdown(.md)을 HTML로 변환하고 Mermaid/LaTeX 수식을 PNG 이미지로 렌더링합니다."
    )
    parser.add_argument("input", help="입력 Markdown 파일 경로 (.md)")
    parser.add_argument("-o", "--output", help="출력 HTML 파일 경로 (.html)")
    parser.add_argument("--title", default=None, help="HTML 문서 제목")
    parser.add_argument("--base64", action="store_true", help="PNG 이미지를 Base64로 인코딩하여 HTML에 임베드")
    args = parser.parse_args()

    in_path = args.input
    if not os.path.isfile(in_path):
        logging.warning(f"파일을 찾을 수 없습니다: {in_path}")
        sys.exit(1)

    with open(in_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    title = args.title or os.path.splitext(os.path.basename(in_path))[0]
    html = md_to_html(
        md_text, 
        title=title,
        use_base64=args.base64
    )

    out_path = args.output or os.path.splitext(in_path)[0] + ".html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    _cleanup_browser()
    logging.info(f"생성 완료: {out_path}")

if __name__ == "__main__":
    main()
