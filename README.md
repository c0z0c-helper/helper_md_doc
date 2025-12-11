# helper-md-doc

[![PyPI version](https://badge.fury.io/py/helper-md-doc.svg)](https://badge.fury.io/py/helper-md-doc)
[![Python](https://img.shields.io/pypi/pyversions/helper-md-doc.svg)](https://pypi.org/project/helper-md-doc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Markdown/HTML을 DOCX로 변환하는 Python 라이브러리 (Mermaid 다이어그램 및 LaTeX 수식 지원)

## 주요 기능

- **Markdown → HTML 변환**: Mermaid 다이어그램과 LaTeX 수식을 PNG 이미지로 렌더링
- **HTML → DOCX 변환**: 이미지와 수식을 임베딩하여 DOCX 생성
- **Markdown → DOCX 직접 변환**: 원스텝 변환 지원
- **Mermaid 지원**: 플로우차트, 시퀀스 다이어그램 등 자동 렌더링
- **LaTeX 수식 지원**: KaTeX 기반 수식 렌더링
- **이미지 임베딩**: Base64 인코딩 또는 파일 경로 지원

## 설치

### 기본 설치
```bash
pip install helper-md-doc

# 테스트 서버
pip install --index-url https://test.pypi.org/simple/ helper-md-doc
```

### Playwright 브라우저 설치 (필수)
```bash
playwright install chromium
```

### Pandoc 설치 (필수)
- **Windows**: https://pandoc.org/installing.html
- **Mac**: `brew install pandoc`
- **Linux**: `sudo apt-get install pandoc`

## 사용법

### 1. Markdown → HTML 변환

```python
from helper_md_doc import md_to_html

md_text = """
# 제목

이것은 **Markdown** 문서입니다.

## Mermaid 다이어그램
```mermaid
graph LR
    A[시작] --> B[처리]
    B --> C[종료]
```

## LaTeX 수식
인라인 수식: $E = mc^2$

블록 수식:
$$
\\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}
$$
"""

html = md_to_html(md_text, title="문서 제목", use_base64=True)
print(html)
```

### 2. HTML → DOCX 변환

```python
from helper_md_doc import html_to_doc

html_to_doc("input.html", "output.docx")
```

### 3. Markdown → DOCX 직접 변환

```python
from helper_md_doc import md_to_doc

md_to_doc("input.md", "output.docx", title="문서 제목")
```

### 4. CLI 사용

```bash
# Markdown → HTML
md2html input.md -o output.html --base64

# HTML → DOCX
html2doc input.html -o output.docx

# Markdown → DOCX
md2doc input.md -o output.docx --title "문서 제목"
```

또는 모듈로 실행:

```bash
# Markdown → HTML
python -m helper_md_doc.helper_md_html input.md -o output.html --base64

# HTML → DOCX
python -m helper_md_doc.helper_html_doc input.html -o output.docx

# Markdown → DOCX
python -m helper_md_doc.helper_md_doc input.md -o output.docx --title "문서 제목"
```

## 의존성

- **markdown** (>=3.7.0): Markdown 파싱
- **playwright** (>=1.40.0): Mermaid/LaTeX 렌더링
- **pypandoc** (>=1.13): DOCX 변환

## 개발

```bash
# 저장소 클론
git clone https://github.com/c0z0c-helper/helper_md_doc.git
cd helper_md_doc

# 편집 모드 설치
pip install -e .

# 개발 의존성 설치
pip install -r requirements-dev.txt

# 테스트 실행
pytest
```

## 라이센스

MIT License

본 패키지는 다음 서드파티 라이브러리를 포함합니다:
- **KaTeX** (MIT License) - LaTeX 수식 렌더링
- **KaTeX Fonts** (SIL Open Font License 1.1) - 수식용 폰트
- **Mermaid** (MIT License) - 다이어그램 렌더링

자세한 내용은 [THIRD_PARTY_LICENSES.md](https://github.com/c0z0c-helper/helper_md_doc/blob/master/THIRD_PARTY_LICENSES.md)를 참조하세요.

## 기여

버그 리포트나 기능 제안은 [GitHub Issues](https://github.com/c0z0c-helper/helper_md_doc/issues)에 등록해주세요.

## 변경 이력

### v0.5.1(2025-12-09)
- 최초 릴리스

### v0.5.2(2025-12-09)
- BOM 처리
- ** 속성 적용

### v0.5.5(2025-12-11)
- 종속 라이브러리 설치
