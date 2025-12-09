"""
helper-md_doc PyPI 업로드 스크립트

사용법:
    python upload_helper_md_doc.py [--test]
    
옵션:
    --test: TestPyPI에 업로드 (기본값: PyPI)
"""

import subprocess
import sys
import shutil
from pathlib import Path


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
    
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print(f"{repo_name} 업로드 실패")
        sys.exit(1)
    
    print(f"{repo_name} 업로드 완료\n")


def main():
    """메인 실행 함수"""
    test_mode = "--test" in sys.argv
    
    print("=" * 60)
    print("helper-md_doc PyPI 업로드")
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
        print("   pip install --index-url https://test.pypi.org/simple/ helper-md_doc")
    else:
        print("PyPI에서 설치:")
        print("   pip install helper-md_doc")
    
    print()
    print("모든 작업 완료!")


if __name__ == "__main__":
    main()
