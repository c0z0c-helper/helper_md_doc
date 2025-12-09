# helper-md_doc pip 업로드 가이드

## 사전 준비

### 1. PyPI 계정 생성
- PyPI: https://pypi.org/account/register/
- TestPyPI: https://test.pypi.org/account/register/

### 2. API 토큰 생성
1. PyPI 계정 로그인
2. Account Settings → API tokens
3. "Add API token" 클릭
4. Token name 입력 (예: helper-md_doc)
5. Scope: "Entire account" 또는 특정 프로젝트 선택
6. 생성된 토큰 복사 (한 번만 표시됨!)

### 3. `.pypirc` 파일 설정 (홈 디렉토리)
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgE... (실제 토큰으로 대체)

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgE... (TestPyPI 토큰으로 대체)
```

**위치**:
- Windows: `C:\Users\<username>\.pypirc`
- Linux/Mac: `~/.pypirc`

## 빌드 도구 설치

```bash
pip install --upgrade build twine
```

## 배포 프로세스

### 1. 버전 업데이트
`pyproject.toml`에서 버전 번호 수정:
```toml
[project]
version = "0.5.0"  # 예: 0.5.1, 0.6.0 등으로 변경
```

`src/helper_md_doc/__init__.py`에서도 동일하게 수정:
```python
__version__ = "0.5.0"
```

### 2. 로컬 테스트

```bash
cd helper_md_doc
python test_install.py
```

### 3. 수동 빌드 (선택사항)

```bash
python -m build
```

빌드 결과 확인:
```bash
# dist/ 디렉토리에 .whl과 .tar.gz 파일 생성됨
ls dist/

# .whl 파일 내용 확인 (정적 파일 포함 여부 체크)
unzip -l dist/helper_md_doc-0.1.0-py3-none-any.whl | grep -E "katex|mermaid"
```

### 4. TestPyPI에 업로드 (테스트용)

```bash
python upload_helper_md_doc.py --test
```

### 5. TestPyPI에서 설치 테스트

```bash
# 새 가상환경 생성 권장
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

# TestPyPI에서 설치
pip install --index-url https://test.pypi.org/simple/ helper-md_doc

# 필수 의존성 설치 (TestPyPI에는 없을 수 있음)
pip install markdown playwright pypandoc

# Playwright 브라우저 설치
playwright install chromium

# 기능 테스트
python -c "from helper_md_doc import md_to_html; print('Import OK')"

# CLI 테스트
md2html --help
```

### 6. PyPI에 업로드 (프로덕션)

테스트가 성공하면 실제 PyPI에 업로드:

```bash
python upload_helper_md_doc.py
```

### 7. PyPI에서 설치 테스트

```bash
pip install helper-md_doc
playwright install chromium

# 테스트
python -c "from helper_md_doc import md_to_html, __version__; print(f'Version: {__version__}')"
```

## 문제 해결

### 문제 1: "File already exists" 에러
**원인**: 같은 버전 번호로 이미 업로드됨  
**해결**: `pyproject.toml`과 `__init__.py`의 버전 번호를 증가시킨 후 재업로드

### 문제 2: 정적 파일(KaTeX 폰트 등)이 포함되지 않음
**원인**: `MANIFEST.in` 또는 `pyproject.toml`의 `package-data` 설정 오류  
**해결**:
1. `MANIFEST.in` 확인:
   ```
   recursive-include src/helper_md_doc/katex/fonts *.ttf *.woff *.woff2
   ```
2. `pyproject.toml` 확인:
   ```toml
   [tool.setuptools.package-data]
   helper_md_doc = ["katex/fonts/*.ttf", ...]
   ```
3. 빌드 후 `.whl` 파일 압축 해제하여 파일 포함 여부 확인

### 문제 3: Import 에러
**원인**: 상대 import 누락  
**해결**: 모든 내부 import를 `.module` 형태로 변경
```python
# 잘못된 예
from helper_md_html import md_to_html

# 올바른 예
from .helper_md_html import md_to_html
```

### 문제 4: Playwright 설치 안내 부족
**해결**: README에 명확히 안내 추가
```bash
playwright install chromium
```

### 문제 5: Pandoc 미설치
**해결**: README에 OS별 설치 방법 명시
- Windows: https://pandoc.org/installing.html
- Mac: `brew install pandoc`
- Linux: `sudo apt-get install pandoc`

## 버전 관리 전략

### Semantic Versioning (권장)
- **Major (X.0.0)**: 하위 호환성 없는 변경
- **Minor (0.X.0)**: 하위 호환성 있는 기능 추가
- **Patch (0.0.X)**: 버그 수정

예시:
- `0.5.0`: 초기 릴리스
- `0.5.1`: 버그 수정
- `0.6.0`: 새 기능 추가
- `1.0.0`: 안정 버전 (프로덕션 준비 완료)

## 추가 명령어

### 패키지 정보 확인
```bash
pip show helper-md_doc
```

### 패키지 삭제
```bash
pip uninstall helper-md_doc
```

### 특정 버전 설치
```bash
pip install helper-md_doc==0.5.0
```

### 최신 버전으로 업그레이드
```bash
pip install --upgrade helper-md_doc
```

## 체크리스트

배포 전 확인사항:

- [ ] 버전 번호 증가 (`pyproject.toml`, `__init__.py`)
- [ ] 로컬 테스트 성공 (`python test_install.py`)
- [ ] TestPyPI 업로드 및 설치 테스트 성공
- [ ] 정적 파일(KaTeX 폰트 등) 포함 확인
- [ ] README.md 업데이트 (변경사항, 사용법 등)
- [ ] CHANGELOG.md 작성 (선택사항)
- [ ] Git 태그 생성: `git tag v0.5.0 && git push origin v0.5.0`

## 참고 자료

- Python Packaging Guide: https://packaging.python.org/
- PyPI: https://pypi.org/
- TestPyPI: https://test.pypi.org/
- Setuptools Documentation: https://setuptools.pypa.io/
- Twine Documentation: https://twine.readthedocs.io/
