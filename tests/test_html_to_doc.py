"""Tests for HTML to DOCX conversion"""

import pytest
import os
import tempfile
from helper_md_doc import clean_html_for_pandoc, embed_images_as_base64


def test_clean_html_for_pandoc():
    """HTML 정리 함수 테스트"""
    html = """
    <html>
    <head><style>body { color: red; }</style></head>
    <body>
        <script>alert('test');</script>
        <h1>제목</h1>
        <p>내용</p>
    </body>
    </html>
    """
    
    cleaned = clean_html_for_pandoc(html)
    
    # style과 script 태그가 제거되었는지 확인
    assert "<style>" not in cleaned
    assert "<script>" not in cleaned
    
    # 실제 컨텐츠는 유지되는지 확인
    assert "<h1>제목</h1>" in cleaned
    assert "<p>내용</p>" in cleaned


def test_embed_images_as_base64():
    """Base64 이미지 임베딩 테스트"""
    # 테스트용 간단한 HTML
    html = """
    <html>
    <body>
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" />
    </body>
    </html>
    """
    
    result = embed_images_as_base64(html)
    
    # Base64 이미지가 유지되는지 확인
    assert "data:image/png;base64," in result


def test_embed_images_with_file_path():
    """파일 경로 이미지 처리 테스트"""
    # 존재하지 않는 파일 경로
    html = '<img src="nonexistent.png" />'
    
    result = embed_images_as_base64(html)
    
    # 원본 HTML이 반환되는지 확인 (파일이 없으므로)
    assert "nonexistent.png" in result
