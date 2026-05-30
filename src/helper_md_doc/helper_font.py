#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D2Coding 폰트 설치 및 확인"""

import logging
import os
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s")

_D2CODING_FONT_FILE = os.path.join(os.path.dirname(__file__), "D2Coding.ttc")


def _get_font_install_path() -> str:
    """OS별 사용자 폰트 설치 경로 반환"""
    if sys.platform == "win32":
        return os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Fonts")
    else:
        return os.path.expanduser("~/.local/share/fonts")


def is_d2coding_installed() -> bool:
    """D2Coding 폰트 설치 여부 확인"""
    if sys.platform == "win32":
        system_font = os.path.join(
            os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", "D2Coding.ttc")
        user_font = os.path.join(_get_font_install_path(), "D2Coding.ttc")
        return os.path.isfile(system_font) or os.path.isfile(user_font)
    elif sys.platform == "darwin":
        system_font = "/Library/Fonts/D2Coding.ttc"
        user_font = os.path.join(_get_font_install_path(), "D2Coding.ttc")
        return os.path.isfile(system_font) or os.path.isfile(user_font)
    else:
        user_font = os.path.join(_get_font_install_path(), "D2Coding.ttc")
        system_fonts = ["/usr/share/fonts/D2Coding.ttc", "/usr/local/share/fonts/D2Coding.ttc"]
        return os.path.isfile(user_font) or any(os.path.isfile(p) for p in system_fonts)


def install_d2coding() -> None:
    """D2Coding 폰트 설치 (패키지 내장 D2Coding.ttc를 OS 폰트 디렉토리에 복사)

    설치 경로:
        Windows : %LOCALAPPDATA%\\Microsoft\\Windows\\Fonts
        macOS   : ~/Library/Fonts
        Linux   : ~/.local/share/fonts
    """
    import shutil

    if not os.path.isfile(_D2CODING_FONT_FILE):
        logging.error(f"패키지 내 D2Coding.ttc 파일을 찾을 수 없습니다: {_D2CODING_FONT_FILE}")
        sys.exit(1)

    if is_d2coding_installed():
        logging.debug("D2Coding 폰트가 이미 설치되어 있습니다.")
        return

    font_dir = _get_font_install_path()
    os.makedirs(font_dir, exist_ok=True)
    dest = os.path.join(font_dir, "D2Coding.ttc")
    shutil.copy2(_D2CODING_FONT_FILE, dest)
    logging.info(f"D2Coding 폰트 설치 완료: {dest}")

    if sys.platform not in ("win32", "darwin"):
        try:
            subprocess.check_call(
                ["fc-cache", "-f", font_dir],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            logging.warning("fc-cache 실행 실패. 수동으로 'fc-cache -f' 를 실행해 주세요.")
