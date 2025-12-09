"""Test configuration for pytest"""

import sys
from pathlib import Path

# 테스트 실행 시 src 디렉토리를 Python 경로에 추가
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
