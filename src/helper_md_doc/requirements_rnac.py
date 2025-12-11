import logging
import os
import sys
import subprocess

logging.basicConfig(level=logging.INFO, format="%(message)s")


def read_requirements(req_file: str = "requirements.txt") -> list:
    """requirements.txt에서 패키지 목록 읽기

    Args:
        req_file: requirements.txt 파일 경로

    Returns:
        패키지 목록 (주석, 빈 줄 제외)
    """
    req_path = os.path.join(os.path.dirname(__file__), "..", "..", req_file)
    packages = []

    if os.path.isfile(req_path):
        with open(req_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    pkg_name = (
                        line.split("==")[0]
                        .split(">=")[0]
                        .split("<=")[0]
                        .split(">")[0]
                        .split("<")[0]
                        .strip()
                    )
                    if pkg_name:
                        packages.append(pkg_name)

    return packages


def install_playwright_browsers() -> None:
    """Playwright 브라우저 바이너리 설치"""
    try:
        logging.info("Playwright 브라우저 바이너리 설치 중...")
        subprocess.check_call(
            [sys.executable, "-m", "playwright", "install"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logging.info("Playwright 브라우저 설치 완료")
    except subprocess.CalledProcessError as e:
        logging.error(f"Playwright 브라우저 설치 실패: {e}")
        sys.exit(1)


def install_requirements():
    """requirements.txt의 라이브러리 자동 설치"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    except subprocess.CalledProcessError as e:
        logging.error(f"종속성 설치 실패: {e}")
        sys.exit(1)


def check_and_print_dependencies() -> None:
    """설치 필요한 종속성 라이브러리를 출력하고 종료

    pip install ... 형식으로 누락된 패키지를 출력한다.
    """
    required_packages = read_requirements()
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if not missing_packages:
        return

    message = "\n"
    message += "-" * 80 + "\n"
    message += "설치 필요한 페키지\n"
    message += f"pip install {' '.join(missing_packages)}\n"
    raise ImportError(message)


def check_and_install_dependencies() -> None:
    """필요한 라이브러리 확인 및 사용자 선택에 따라 설치

    옵션:
        a: 자동 설치 (모든 패키지 일괄, 기본값)
        y: 수동 설치 (각 패키지별 확인)
        n: 건너뛰기 (설치 안 함)
        c: 취소 (프로그램 종료)
    """
    required_packages = read_requirements()
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if not missing_packages:
        logging.debug("모든 필수 라이브러리가 설치되어 있습니다.")
        # playwright 브라우저 바이너리 확인
        _check_playwright_browsers()
        return

    logging.warning("다음 라이브러리가 설치되지 않았습니다:")
    for pkg in missing_packages:
        logging.warning(f"  - {pkg}")

    while True:
        response = (
            input("\n설치 옵션을 선택하세요 (all/yes/no/cancel) (a/y/n/c, 기본값 a): ")
            .strip()
            .lower()
            or "a"
        )

        if response == "a":
            logging.info("모든 패키지를 자동 설치합니다...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install"] + missing_packages,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logging.info("설치 완료")
            except subprocess.CalledProcessError as e:
                logging.error(f"설치 실패: {e}")
                sys.exit(1)

            # playwright 패키지가 설치된 경우 브라우저 바이너리도 설치
            if "playwright" in missing_packages:
                install_playwright_browsers()
            break

        elif response == "y":
            logging.info("각 패키지별로 설치 여부를 확인합니다...")
            playwright_installed = False
            for pkg in missing_packages:
                user_input = input(f"'{pkg}' 설치하시겠습니까? (y/n): ").strip().lower()
                if user_input == "y":
                    try:
                        subprocess.check_call(
                            [sys.executable, "-m", "pip", "install", pkg],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        logging.info(f"'{pkg}' 설치 완료")
                        if pkg == "playwright":
                            playwright_installed = True
                    except subprocess.CalledProcessError as e:
                        logging.error(f"'{pkg}' 설치 실패: {e}")
                else:
                    logging.info(f"'{pkg}' 설치를 건너뜁니다.")

            # playwright가 설치된 경우 브라우저 바이너리도 설치
            if playwright_installed:
                install_playwright_browsers()
            break

        elif response == "n":
            logging.warning(
                "라이브러리 설치를 건너뜁니다. 프로그램 실행 중 오류가 발생할 수 있습니다."
            )
            break

        elif response == "c":
            logging.info("프로그램을 취소합니다.")
            sys.exit(0)

        else:
            logging.warning("잘못된 입력입니다. a/y/n/c 중 하나를 선택하세요.")


def _check_playwright_browsers() -> None:
    """Playwright 브라우저 바이너리 확인 및 필요시 설치"""
    try:
        __import__("playwright")
        # playwright가 설치되어 있으면 브라우저 바이너리 확인
        from playwright.sync_api import sync_playwright

        try:
            # 빠른 확인을 위해 타임아웃 설정
            with sync_playwright() as p:
                pass
        except Exception:
            # 브라우저 바이너리가 없으면 설치
            logging.warning("Playwright 브라우저 바이너리가 없습니다.")
            response = (
                input("Playwright 브라우저를 설치하시겠습니까? (y/n, 기본값 y): ").strip().lower()
                or "y"
            )
            if response == "y":
                install_playwright_browsers()
    except ImportError:
        pass
