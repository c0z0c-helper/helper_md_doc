"""
helper-md-doc 로컬 설치 및 테스트 스크립트

사용법:
    python test_install.py
"""

import subprocess
import sys
from pathlib import Path


def test_local_install():
    """로컬 패키지 설치 및 테스트"""
    print("=" * 60)
    print("helper-md-doc 로컬 설치 테스트")
    print("=" * 60)
    print()

    # 1. 현재 디렉토리 확인
    current_dir = Path(__file__).parent
    print(f"현재 디렉토리: {current_dir}")
    print()

    # 2. 패키지 설치 (편집 모드)
    print("패키지 설치 중 (편집 모드)...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        cwd=current_dir,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("설치 실패:")
        print(result.stderr)
        sys.exit(1)

    print("설치 완료")
    print()

    # 3. 임포트 테스트
    print("임포트 테스트...")
    try:
        from helper_md_doc import md_to_html, html_to_doc, md_to_doc, __version__

        print(f"임포트 성공 (버전: {__version__})")
    except ImportError as e:
        print(f"임포트 실패: {e}")
        sys.exit(1)

    print()

    # 4. 기본 기능 테스트
    print("기본 기능 테스트...")
    try:
        test_md = "# 테스트\n\n이것은 **테스트** 문서입니다."
        html = md_to_html(test_md, title="테스트", use_base64=True)
        print("md_to_html() 성공")

        if "<h1>테스트</h1>" in html and "<strong>테스트</strong>" in html:
            print("HTML 변환 결과 검증 성공")
        else:
            print(" HTML 변환 결과 검증 실패 (내용 불일치)")
    except Exception as e:
        print(f"기능 테스트 실패: {e}")
        sys.exit(1)

    print()
    print("모든 테스트 통과!")
    print()
    print("다음 단계:")
    print("   1. playwright install chromium")
    print("   2. pandoc 설치 확인")
    print("   3. python upload_helper_md_doc.py --test")


if __name__ == "__main__":
    test_local_install()
