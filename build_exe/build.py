#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md2doc Windows 독립 실행 파일 빌드 스크립트
사용법: python build_exe/build.py

사전 요건:
  pip install pyinstaller
  playwright install chromium
  pandoc 설치 (https://pandoc.org/installing.html)
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_PKG = ROOT / "src" / "helper_md_doc"
ENTRY = ROOT / "build_exe" / "entry_md2doc.py"
DIST_DIR = ROOT / "dist"
BUILD_TMP = ROOT / "build_exe" / "_build_tmp"


# ---------------------------------------------------------------------------
# 경로 탐지 헬퍼
# ---------------------------------------------------------------------------

def get_pandoc_path() -> str:
    """pandoc 실행 파일 경로 반환 (pypandoc → PATH 순서로 탐색)"""
    # 1. pypandoc 내장 탐색
    try:
        import pypandoc
        path = pypandoc.get_pandoc_path()
        if path and os.path.isfile(path):
            return path
    except Exception:
        pass

    # 2. PATH 탐색
    found = shutil.which("pandoc")
    if found:
        return found

    raise RuntimeError(
        "pandoc 실행 파일을 찾을 수 없습니다.\n"
        "설치: https://pandoc.org/installing.html"
    )


def get_playwright_chromium_path() -> Path:
    """Playwright Chromium 디렉토리 경로 반환"""
    # PLAYWRIGHT_BROWSERS_PATH 환경변수 우선
    custom = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    search_roots = []
    if custom:
        search_roots.append(Path(custom))

    # 기본 경로
    local_app = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    search_roots.append(local_app)

    # playwright 패키지 내부 드라이버 경로 (일부 환경)
    try:
        import playwright
        pw_pkg = Path(playwright.__file__).parent
        search_roots.append(pw_pkg / "driver" / "package" / ".local-chromium")
        search_roots.append(pw_pkg / ".local-browsers")
    except ImportError:
        pass

    for root in search_roots:
        if not root.exists():
            continue
        candidates = sorted(root.glob("chromium-*"), reverse=True)
        if candidates:
            return candidates[0]

    raise RuntimeError(
        "Playwright Chromium 브라우저를 찾을 수 없습니다.\n"
        "실행: playwright install chromium"
    )


# ---------------------------------------------------------------------------
# 빌드
# ---------------------------------------------------------------------------

def build():
    print("=" * 60)
    print("md2doc 독립 실행 파일 빌드")
    print("=" * 60)

    # 필수 도구 확인
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller 설치 중...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller"])

    pandoc_exe = get_pandoc_path()
    chromium_dir = get_playwright_chromium_path()
    chromium_name = chromium_dir.name  # e.g. chromium-1148

    print(f"  Pandoc   : {pandoc_exe}")
    print(f"  Chromium : {chromium_dir}")
    print()

    # 이전 빌드 정리
    exe_out = DIST_DIR / "md2doc.exe"
    if exe_out.exists():
        exe_out.unlink()
    if (DIST_DIR / "md2doc").exists():
        shutil.rmtree(DIST_DIR / "md2doc")
    if BUILD_TMP.exists():
        shutil.rmtree(BUILD_TMP)

    # --add-data / --add-binary 인수 구성 (Windows 구분자: ';')
    sep = ";"

    # latex2mathml 데이터 파일 경로 탐색
    import importlib.util as _ilu
    _l2m_spec = _ilu.find_spec("latex2mathml")
    _l2m_dir = Path(
        _l2m_spec.submodule_search_locations[0]) if _l2m_spec else None

    data_args = [
        # pandoc 실행 파일
        f"--add-binary={pandoc_exe}{sep}.",
        # Playwright Chromium (전체 디렉토리)
        f"--add-data={chromium_dir}{sep}playwright_browsers/{chromium_name}",
        # 패키지 데이터
        f"--add-data={SRC_PKG / 'katex'}{sep}helper_md_doc/katex",
        f"--add-data={SRC_PKG / 'mermaid'}{sep}helper_md_doc/mermaid",
        f"--add-data={SRC_PKG / 'D2Coding.ttc'}{sep}helper_md_doc",
    ]

    # latex2mathml 데이터 파일 (unimathsymbols.txt 등) 추가
    if _l2m_dir and _l2m_dir.exists():
        for _txt in _l2m_dir.glob("*.txt"):
            data_args.append(f"--add-data={_txt}{sep}latex2mathml")
        for _xml in _l2m_dir.glob("*.xml"):
            data_args.append(f"--add-data={_xml}{sep}latex2mathml")

    # reference.docx (선택)
    ref_doc = SRC_PKG / "reference.docx"
    if ref_doc.exists():
        data_args.append(f"--add-data={ref_doc}{sep}helper_md_doc")

    hidden_imports = [
        # playwright: sync_api + async_api 모두 필요
        # (helper_html_pdf.py가 async_playwright 사용, __init__.py가 전부 import)
        "--hidden-import=playwright.sync_api",
        "--hidden-import=playwright.async_api",
        "--hidden-import=playwright._impl._api_types",
        "--hidden-import=playwright._impl._connection",
        "--hidden-import=pypandoc",
        "--hidden-import=markdown",
        "--hidden-import=markdown.extensions.fenced_code",
        "--hidden-import=markdown.extensions.tables",
        "--hidden-import=latex2mathml",
        "--hidden-import=latex2mathml.converter",
        "--hidden-import=latex2mathml.symbols_parser",
        "--hidden-import=latex2mathml.tokenizer",
        "--hidden-import=latex2mathml.walker",
        "--hidden-import=latex2mathml.node",
        "--hidden-import=latex2mathml.exceptions",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageChops",
        # helper_md_doc 전체 서브모듈 (__init__.py가 전부 import하므로 모두 필요)
        "--hidden-import=helper_md_doc",
        "--hidden-import=helper_md_doc.requirements_rnac",
        "--hidden-import=helper_md_doc.helper_md_html",
        "--hidden-import=helper_md_doc.helper_html_doc",
        "--hidden-import=helper_md_doc.helper_md_doc",
        "--hidden-import=helper_md_doc.helper_md_text",
        "--hidden-import=helper_md_doc.helper_html_md",
        "--hidden-import=helper_md_doc.helper_doc_html",
        "--hidden-import=helper_md_doc.helper_md_pdf",
        "--hidden-import=helper_md_doc.helper_html_pdf",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "md2doc",
        "--console",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_TMP}",
        f"--specpath={ROOT / 'build_exe'}",
        *data_args,
        *hidden_imports,
        # 불필요한 모듈 제외 (용량 절감)
        "--exclude-module=tkinter",
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        str(ENTRY),
    ]

    print("PyInstaller 실행 중...")
    subprocess.check_call(cmd)

    exe_path = DIST_DIR / "md2doc.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / 1024 / 1024
        print()
        print("=" * 60)
        print(f"빌드 완료: {exe_path}")
        print(f"단일 파일 크기: {size_mb:.1f} MB")
        print("=" * 60)
        print()
        print("사용법:")
        print(f"  {exe_path} input.md")
        print(f"  {exe_path} input.md -o output.docx")
        print()
        print("참고:")
        print("  최초 실행 시 %LOCALAPPDATA%\\md2doc\\cache 에 파일을 추출합니다.")
        print("  이후 실행부터는 캐시를 재사용하여 빠르게 기동합니다.")
    else:
        print("빌드 실패: md2doc.exe 생성되지 않음", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    build()
