"""여러 helper_md_doc 서브모듈을 임포트해도 Playwright 브라우저 설치 확인이
한 번만 수행되는지 검증 (회귀 테스트).

배경 1: 각 서브모듈이 자체적으로 requirements_rnac.check_and_install_dependencies()를
호출하는데, 과거에는 spec_from_file_location으로 requirements_rnac을 매번 새
모듈 인스턴스로 로드하여 모듈 간 상태(가드 플래그)가 공유되지 않았다. 그 결과
`md2doc` 실행 한 번에 확인 절차가 8번 반복 수행되었다.

배경 2: 브라우저 설치 확인(_check_playwright_browsers)은 원래 메인 프로세스
안에서 직접 `with sync_playwright() as p: pass`를 실행했으나, 이는 이후 실제
렌더링에서 또 다른 sync_playwright 세션을 여는 것과 겹쳐 Windows에서
"Task was destroyed but it is pending!" / TargetClosedError를 유발했다.
그래서 확인 절차 자체를 별도 서브프로세스로 격리했다 (requirements_rnac.py의
_check_playwright_browsers 참고). 이 테스트는 그 확인용 서브프로세스가
가드 플래그 덕분에 여러 서브모듈 임포트에도 불구하고 정확히 1번만 실행되는지
검증한다 (실제 chromium을 띄우지 않도록 subprocess.run 자체를 가짜로 대체한다).
"""

import subprocess
import sys
from pathlib import Path

SRC_PATH = Path(__file__).parent.parent / "src"

_PROBE_SCRIPT = """
import sys
sys.path.insert(0, r"{src_path}")

count = {{"n": 0}}
import subprocess as sp
orig_run = sp.run


class _FakeCompleted:
    returncode = 0


def counting_run(cmd, *a, **kw):
    if (
        isinstance(cmd, list)
        and len(cmd) >= 3
        and cmd[1] == "-c"
        and "sync_playwright" in cmd[2]
    ):
        count["n"] += 1
        return _FakeCompleted()
    return orig_run(cmd, *a, **kw)


sp.run = counting_run

import helper_md_doc  # noqa: F401  (전체 서브모듈 임포트를 트리거)

print(count["n"])
"""


def test_playwright_browser_check_run_once_across_all_submodule_imports() -> None:
    script = _PROBE_SCRIPT.format(src_path=str(SRC_PATH))
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    check_count = int(result.stdout.strip().splitlines()[-1])
    assert check_count == 1, (
        f"Playwright 브라우저 확인이 {check_count}번 수행되었습니다 (기대값: 1). "
        "requirements_rnac 모듈이 서브모듈 간 공유되지 않으면 확인 절차가 "
        "여러 번 반복 수행됩니다."
    )
