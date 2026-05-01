"""
helper-md-doc PyPI 업로드 스크립트

사용법:
    python upload_helper_md_doc.py [--test]

옵션:
    --test: TestPyPI에 업로드 (기본값: PyPI)
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

# Windows cp949 터미널에서 twine/rich의 유니코드 출력 오류 방지
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def clean_build():
    """빌드 디렉토리 정리"""
    print("빌드 디렉토리 정리 중...")
    dirs_to_clean = ["build", "dist", "*.egg-info"]
    for pattern in dirs_to_clean:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"   삭제: {path}")
    print("정리 완료\n")


def build_package():
    """패키지 빌드"""
    print("패키지 빌드 중...")
    result = subprocess.run([sys.executable, "-m", "build"], capture_output=True, text=True)

    if result.returncode != 0:
        print("빌드 실패:")
        print(result.stderr)
        sys.exit(1)

    print("빌드 완료\n")
    return result


def upload_package(test_mode=False):
    """패키지 업로드"""
    repository = "testpypi" if test_mode else "pypi"
    repo_name = "TestPyPI" if test_mode else "PyPI"

    print(f"{repo_name}에 업로드 중...")

    cmd = [sys.executable, "-m", "twine", "upload"]
    if test_mode:
        cmd.extend(["--repository", "testpypi"])
    cmd.append("dist/*")

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # NO_COLOR=1: rich의 유니코드 진행 표시 비활성화 → cp949 UnicodeEncodeError 방지
    env["NO_COLOR"] = "1"

    if sys.platform == "win32":
        # 콘솔 코드페이지를 UTF-8(65001)로 변경 (chcp 65001)
        subprocess.run(["chcp", "65001"], shell=True, capture_output=True)

    result = subprocess.run(cmd, env=env)

    if result.returncode != 0:
        print(f"{repo_name} 업로드 실패")
        sys.exit(1)

    print(f"{repo_name} 업로드 완료\n")


def main():
    """메인 실행 함수"""
    test_mode = "--test" in sys.argv

    print("=" * 60)
    print("helper-md-doc PyPI 업로드")
    print("=" * 60)
    print()

    # 1. 빌드 디렉토리 정리
    clean_build()

    # 2. 패키지 빌드
    build_package()

    # 3. 패키지 업로드
    upload_package(test_mode)

    # 4. 완료 메시지
    if test_mode:
        print("TestPyPI에서 설치 테스트:")
        print("   pip install --index-url https://test.pypi.org/simple/ helper-md-doc")
    else:
        print("PyPI에서 설치:")
        print("   pip install helper-md-doc")

    print()
    print("모든 작업 완료!")


if __name__ == "__main__":
    main()
