#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md2doc PyInstaller 진입점 (--onefile)

frozen 환경에서 실행 시:
  1. exe 버전 식별자(크기+mtime)로 캐시 디렉토리 결정
  2. 캐시 미존재 시 sys._MEIPASS → %LOCALAPPDATA%\md2doc\cache\<id> 복사
  3. 캐시 경로 기준으로 환경변수 설정
     - PLAYWRIGHT_BROWSERS_PATH
     - PYPANDOC_PANDOC
"""

from helper_md_doc.helper_md_doc import main
import os
import sys


def _resolve_base() -> str:
    """캐시 디렉토리 경로 반환.
    첫 실행: _MEIPASS → 캐시 복사 후 반환
    재실행 : 기존 캐시 바로 반환 (빠른 기동)
    """
    import shutil
    import tempfile

    meipass = sys._MEIPASS

    # exe 크기+mtime 으로 버전 식별 (업데이트 시 자동 재캐시)
    exe = sys.executable
    stat = os.stat(exe)
    version_id = f"{stat.st_size}_{int(stat.st_mtime)}"

    cache_root = os.path.join(
        os.environ.get("LOCALAPPDATA", tempfile.gettempdir()),
        "md2doc", "cache", version_id,
    )

    if not os.path.isdir(cache_root):
        # 이전 버전 캐시 정리 (용량 관리)
        parent = os.path.dirname(cache_root)
        if os.path.isdir(parent):
            for old in os.listdir(parent):
                old_path = os.path.join(parent, old)
                if old != version_id and os.path.isdir(old_path):
                    shutil.rmtree(old_path, ignore_errors=True)

        print(f"[md2doc] 초기 설정 중... (최초 1회, {cache_root})", flush=True)
        os.makedirs(cache_root, exist_ok=True)
        shutil.copytree(meipass, cache_root, dirs_exist_ok=True)
        print("[md2doc] 초기 설정 완료.", flush=True)

    return cache_root


if getattr(sys, "frozen", False):
    _base = _resolve_base()

    # 1. Playwright Chromium 경로
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
        _base, "playwright_browsers")

    # 2. Pandoc 실행 파일 경로
    _pandoc_exe = os.path.join(_base, "pandoc.exe")
    if os.path.isfile(_pandoc_exe):
        os.environ["PYPANDOC_PANDOC"] = _pandoc_exe

    # 3. 패키지 루트 sys.path 등록
    if _base not in sys.path:
        sys.path.insert(0, _base)


if __name__ == "__main__":
    main()
