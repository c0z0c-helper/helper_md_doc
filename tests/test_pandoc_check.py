"""pandoc 실행 파일 자동 확인/설치 검증 (회귀 테스트).

배경: pypandoc은 pip 패키지일 뿐이며, 실제 변환에 필요한 pandoc 실행 파일은
별도로 PATH에 있거나 로컬 설치되어 있어야 한다. 과거에는 requirements_rnac이
pip 패키지 유무만 확인하고 pandoc 바이너리 유무는 확인하지 않아, pandoc이
없는 환경(예: 새 PC)에서 `md2doc` 실행이 `OSError: No pandoc was found`로
끝까지 실패했다.
"""

from unittest.mock import patch

import pytest

from helper_md_doc import requirements_rnac as rn


@pytest.fixture(autouse=True)
def _reset_pandoc_guard():
    rn._pandoc_checked = False
    yield
    rn._pandoc_checked = False


def test_pandoc_missing_triggers_download_once():
    with patch("pypandoc.get_pandoc_path", side_effect=OSError("No pandoc was found")), \
         patch("pypandoc.download_pandoc") as mock_download, \
         patch("builtins.input", return_value="y"):
        rn._check_pandoc_installed()
        rn._check_pandoc_installed()  # 두 번째 호출은 가드로 인해 no-op이어야 함

    assert mock_download.call_count == 1


def test_pandoc_present_skips_download():
    with patch("pypandoc.get_pandoc_path", return_value="/usr/bin/pandoc"), \
         patch("pypandoc.download_pandoc") as mock_download:
        rn._check_pandoc_installed()

    mock_download.assert_not_called()
