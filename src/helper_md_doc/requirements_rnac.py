import logging
import os
import subprocess
import sys

from helper_md_doc.helper_font import install_d2coding

logging.basicConfig(level=logging.INFO, format="%(message)s")

# check_and_install_dependencies()가 여러 모듈에서 반복 호출되어도
# Playwright 드라이버 프로세스를 한 번만 기동/확인하도록 하는 가드
_playwright_browsers_checked = False

# check_and_install_dependencies()가 여러 모듈에서 반복 호출되어도
# pandoc 바이너리 확인/설치를 한 번만 수행하도록 하는 가드
_pandoc_checked = False

# check_and_install_dependencies()가 여러 모듈에서 반복 호출되어도
# "확인 완료" 로그가 모듈 수만큼 중복 출력되지 않도록 하는 가드
_dependencies_checked = False


# 설치명(pip)과 임포트명이 다른 패키지 매핑
_IMPORT_NAME_MAP: dict = {
    "Pillow": "PIL",
    "pillow": "PIL",
    "scikit-learn": "sklearn",
    "scikit_learn": "sklearn",
    "python-dateutil": "dateutil",
    "python_dateutil": "dateutil",
    "opencv-python": "cv2",
    "opencv_python": "cv2",
    "beautifulsoup4": "bs4",
    "beautifulsoup4": "bs4",
    "pyyaml": "yaml",
    "PyYAML": "yaml",
}


def read_requirements(req_file: str = "requirements.txt") -> list:
    """패키지 의존성 목록 읽기

    우선순위:
        1. importlib.metadata: pip 설치 환경에서 pyproject.toml의 dependencies 사용
        2. requirements.txt: 소스 개발 환경 fallback

    Args:
        req_file: requirements.txt 파일 경로 (fallback용)

    Returns:
        패키지 목록 (임포트명 기준)
    """
    # 1. pip 설치 환경: pyproject.toml dependencies 참조
    try:
        from importlib.metadata import PackageNotFoundError, requires

        try:
            deps = requires("helper-md-doc") or []
            packages = []
            for dep in deps:
                # "latex2mathml>=3.0.0", "Pillow>=10.0.0 ; extra == 'dev'" 등
                if "; extra ==" in dep:
                    continue
                pkg_name = (
                    dep.split(">=")[0]
                    .split("==")[0]
                    .split("<=")[0]
                    .split(">")[0]
                    .split("<")[0]
                    .split(";")[0]
                    .strip()
                )
                if pkg_name:
                    packages.append(_IMPORT_NAME_MAP.get(pkg_name, pkg_name))
            if packages:
                return packages
        except PackageNotFoundError:
            pass
    except ImportError:
        pass

    # 2. 소스 개발 환경 fallback: requirements.txt 직접 읽기
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
                        packages.append(_IMPORT_NAME_MAP.get(pkg_name, pkg_name))

    return packages


def _prompt(question: str, default: str = "y") -> str:
    """사용자 입력을 받되, 콘솔이 없는 환경(exe 더블클릭 실행 등)에서는
    EOFError로 죽는 대신 기본값을 적용하고 그 사실을 로그로 남긴다.
    """
    try:
        response = input(question).strip().lower()
    except EOFError:
        logging.info(f"(입력을 받을 수 없는 환경입니다. 기본값 '{default}'를 적용합니다)")
        return default
    return response or default


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
    global _dependencies_checked
    if _dependencies_checked:
        return
    _dependencies_checked = True

    required_packages = read_requirements()
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if not missing_packages:
        # logging.info(f"필수 라이브러리 확인 완료: {', '.join(required_packages)}")
        # playwright가 requirements.txt에 있으면 브라우저 바이너리 확인
        if "playwright" in required_packages:
            _check_playwright_browsers()
        # pypandoc이 requirements.txt에 있으면 pandoc 바이너리 확인
        if "pypandoc" in required_packages:
            _check_pandoc_installed()
        # D2Coding 폰트 미설치 시 자동 설치
        install_d2coding()
        return

    logging.warning("다음 라이브러리가 설치되지 않았습니다: " + ", ".join(missing_packages))
    logging.warning("수동 설치 명령어: pip install " + " ".join(missing_packages))

    while True:
        response = _prompt(
            "\n설치 옵션을 선택하세요 (all/yes/no/cancel) (a/y/n/c, 기본값 a): ", default="a"
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
            # pypandoc 패키지가 설치된 경우 pandoc 바이너리도 확인
            if "pypandoc" in missing_packages:
                _check_pandoc_installed()
            break

        elif response == "y":
            logging.info("각 패키지별로 설치 여부를 확인합니다...")
            playwright_installed = False
            pypandoc_installed = False
            for pkg in missing_packages:
                user_input = _prompt(f"'{pkg}' 설치하시겠습니까? (y/n): ", default="y")
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
                        if pkg == "pypandoc":
                            pypandoc_installed = True
                    except subprocess.CalledProcessError as e:
                        logging.error(f"'{pkg}' 설치 실패: {e}")
                else:
                    logging.info(f"'{pkg}' 설치를 건너뜁니다.")

            # playwright가 설치된 경우 브라우저 바이너리도 설치
            if playwright_installed:
                install_playwright_browsers()
            # pypandoc이 설치된 경우 pandoc 바이너리도 확인
            if pypandoc_installed:
                _check_pandoc_installed()
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
    """Playwright 브라우저 바이너리 확인 및 필요시 설치

    주의: playwright가 설치되어 있어야 이 함수를 호출할 수 있습니다.
    """
    global _playwright_browsers_checked
    if _playwright_browsers_checked:
        return

    try:
        import playwright  # noqa: F401
    except ImportError:
        logging.debug("Playwright가 설치되지 않았습니다. 건너뜁니다.")
        _playwright_browsers_checked = True
        return

    try:
        # 메인 프로세스에서 sync_playwright 세션을 시작했다가 바로 종료하면
        # (이후 실제 렌더링에서 다시 세션을 시작할 때) Windows에서 드라이버의
        # 백그라운드 스레드/이벤트 루프가 겹쳐 "Task was destroyed but it is
        # pending!" 경고가 발생할 수 있다. 확인은 별도 프로세스에서 수행해
        # 메인 프로세스의 Playwright 상태에 영향을 주지 않도록 한다.
        check_code = (
            "from playwright.sync_api import sync_playwright\n"
            "with sync_playwright() as p:\n"
            "    b = p.chromium.launch(headless=True)\n"
            "    b.close()\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", check_code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            logging.warning(
                "Playwright 브라우저 바이너리가 없습니다. (md2doc 실행 시 Mermaid/LaTeX 렌더링에 필요)"
            )
            response = _prompt(
                "Playwright 브라우저를 설치하시겠습니까? (y/n, 기본값 y): ", default="y"
            )
            if response == "y":
                install_playwright_browsers()
            else:
                logging.warning(
                    "설치를 건너뜁니다. 수동 설치 명령어: "
                    f"{sys.executable} -m playwright install"
                )
    finally:
        _playwright_browsers_checked = True


def _check_pandoc_installed() -> None:
    """pandoc 바이너리 확인 및 필요시 설치

    pypandoc은 pip 패키지일 뿐, 실제 문서 변환에 필요한 pandoc 실행 파일은
    별도로 PATH에 있거나 pypandoc이 관리하는 로컬 경로에 설치되어 있어야 한다.
    이 함수는 pandoc 실행 파일 유무를 확인하고, 없으면 pypandoc.download_pandoc()으로
    사용자 홈 디렉터리 아래에 로컬 설치한다 (관리자 권한 불필요).

    주의: pypandoc이 설치되어 있어야 이 함수를 호출할 수 있습니다.
    """
    global _pandoc_checked
    if _pandoc_checked:
        return

    try:
        import pypandoc

        try:
            pypandoc.get_pandoc_path()
        except OSError:
            logging.warning("pandoc 실행 파일이 없습니다. (md2doc의 문서 변환에 필요)")
            response = _prompt("pandoc을 설치하시겠습니까? (y/n, 기본값 y): ", default="y")
            if response == "y":
                try:
                    logging.info("pandoc 설치 중...")
                    pypandoc.download_pandoc()
                    logging.info("pandoc 설치 완료")
                except Exception as e:
                    logging.error(f"pandoc 설치 실패: {e}")
                    logging.error("수동 설치: https://pandoc.org/installing.html 참고")
                    sys.exit(1)
            else:
                logging.warning(
                    "설치를 건너뜁니다. 수동 설치: https://pandoc.org/installing.html 참고"
                )
    except ImportError:
        logging.debug("pypandoc이 설치되지 않았습니다. 건너뜁니다.")
    finally:
        _pandoc_checked = True


def run_cli(main_func) -> None:
    """CLI 진입점을 감싸서, 라이브러리/실행 파일 누락으로 인한 원본 예외 대신
    사용자가 바로 조치할 수 있는 설치 안내 메시지를 출력한다.
    """
    try:
        main_func()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        logging.info("사용자에 의해 취소되었습니다.")
        sys.exit(130)
    except ImportError as e:
        logging.error(f"필수 라이브러리가 설치되어 있지 않습니다: {e}")
        logging.error(f"설치 명령어: {sys.executable} -m pip install helper-md-doc --upgrade")
        sys.exit(1)
    except Exception as e:
        msg = str(e)
        if "Executable doesn't exist" in msg or (
            "playwright" in msg.lower() and "install" in msg.lower()
        ):
            logging.error("Playwright 브라우저가 설치되어 있지 않습니다.")
            logging.error(f"설치 명령어: {sys.executable} -m playwright install")
        elif "pandoc" in msg.lower() and (
            "no such file" in msg.lower() or "not found" in msg.lower() or "찾을 수 없" in msg
        ):
            logging.error("pandoc 실행 파일을 찾을 수 없습니다.")
            logging.error(
                "프로그램을 다시 실행하면 자동 설치를 시도합니다. 수동 설치: https://pandoc.org/installing.html"
            )
        else:
            logging.error(f"실행 중 오류가 발생했습니다: {e}")
        sys.exit(1)
