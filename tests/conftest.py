"""Test configuration for pytest"""

import importlib.util
import sys
from pathlib import Path

import pytest

# 테스트 실행 시 src 디렉토리를 Python 경로에 추가
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def chromium_is_available() -> bool:
    if importlib.util.find_spec("playwright.sync_api") is None:
        return False

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        return Path(playwright.chromium.executable_path).exists()


@pytest.fixture
def require_chromium() -> None:
    if not chromium_is_available():
        pytest.skip("Chromium이 설치되지 않아 PDF 테스트를 건너뜁니다.")
