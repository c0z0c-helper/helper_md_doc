"""Tests for helper_md_doc package"""

import pytest
from helper_md_doc import md_to_html, __version__


def test_version():
    """버전이 올바르게 설정되었는지 확인"""
    assert __version__ == "0.5.4"


def test_md_to_html_basic():
    """기본 Markdown → HTML 변환 테스트"""
    md_text = "# 제목\n\n이것은 **굵은 글씨**입니다."
    html = md_to_html(md_text, title="테스트", use_base64=True)

    assert "<h1>제목</h1>" in html
    assert "<strong>굵은 글씨</strong>" in html
    assert "<title>테스트</title>" in html


def test_md_to_html_escaped_bold():
    """이스케이프된 볼드 마커(\\*\\*) 복원 테스트"""
    md_text = (
        "# 테스트\n\n\\*\\*DTLS(Datagram Transport Layer Security)\\*\\*는 보안 프로토콜입니다."
    )
    html = md_to_html(md_text, title="이스케이프 테스트", use_base64=True)

    assert "<strong>DTLS(Datagram Transport Layer Security)</strong>" in html
    assert "**DTLS" not in html  # 리터럴 별표가 남지 않아야 함


def test_md_to_html_with_list():
    """리스트가 포함된 Markdown 변환 테스트"""
    md_text = """
# 리스트 테스트

- 항목 1
- 항목 2
- 항목 3
"""
    html = md_to_html(md_text, title="리스트", use_base64=True)

    assert "<ul>" in html
    assert "<li>항목 1</li>" in html
    assert "<li>항목 2</li>" in html
    assert "<li>항목 3</li>" in html


def test_md_to_html_with_code():
    """코드 블록이 포함된 Markdown 변환 테스트"""
    md_text = """
# 코드 테스트

```python
def hello():
    print("Hello, World!")
```
"""
    html = md_to_html(md_text, title="코드", use_base64=True)

    assert "<pre><code" in html
    assert "def hello():" in html
    assert 'print("Hello, World!")' in html


def test_md_to_html_auto_title():
    """제목 자동 추출 테스트"""
    md_text = "# 자동 제목\n\n내용"
    html = md_to_html(md_text, title=None, use_base64=True)

    assert "<title>자동 제목</title>" in html


def test_md_to_html_no_title():
    """제목이 없는 경우 테스트"""
    md_text = "내용만 있는 문서"
    html = md_to_html(md_text, title=None, use_base64=True)

    assert "<title>Untitled</title>" in html or "<title></title>" in html
