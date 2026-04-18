# task01 - `html2pdf` / `md2pdf` 설계

## 목표

- 신규 기능 `html2pdf`, `md2pdf`를 현재 저장소 구조에 맞게 추가한다.
- 다음 세션에서 바로 구현 가능한 수준의 결정사항과 체크리스트만 유지한다.

## 현재 상태

- 완료: `md2html`은 이미 구현되어 있으며 `pyproject.toml`에 엔트리포인트가 있다.
- 완료: 참고 소스 `D:\project\helper\helper_hwp\helper_hwp`의 PDF CLI 패턴을 확인했다.
- 미구현: `html2pdf`, `md2pdf` 전용 API, CLI, 테스트는 아직 없다.

## 결정사항

- PDF 엔진은 기존 의존성과 일관되게 `playwright`를 사용한다.
- 구현 순서는 `html2pdf` 먼저, `md2pdf`는 그 위에 조합한다.
- `md2pdf`는 `md_to_html(..., use_base64=True)` 결과를 PDF 경로에 연결한다.
- 기본 출력 파일명은 입력 파일 stem 기준 `.pdf`를 사용한다.
- 첫 범위에서는 A4 기본 설정만 지원하고 헤더/푸터, 커스텀 CSS는 제외한다.

## 재검토 문제점

- `md2pdf`가 `html2pdf`의 파일 경로 API만 재사용하면 임시 HTML 파일 관리가 추가된다.
- `helper_md_html._get_browser_page()`는 Mermaid/KaTeX 렌더링용 전역 페이지라 PDF 출력용으로 그대로 재사용하면 책임이 섞인다.
- `html2pdf`는 상대 이미지 경로 해석 기준 디렉터리를 명확히 넘기지 않으면 결과가 달라질 수 있다.
- `md2pdf`에서 Markdown 원본의 상대 이미지 경로는 `md` 파일 부모 경로를 기준으로 다시 해석해야 한다.
- `md_to_html(..., use_base64=True)` 호출 뒤에는 Mermaid/LaTeX 렌더링용 브라우저 정리가 빠지면 세션이 남을 수 있다.
- PDF 테스트는 Chromium 설치 여부 확인 방식이 없으면 환경별로 불안정해질 수 있다.

## 보완 결정

- `html2pdf` 내부에 파일 경로용 API와 HTML 문자열용 내부 헬퍼를 분리한다.
- PDF 출력은 `helper_md_html` 전역 페이지를 직접 재사용하지 않고 PDF 전용 페이지에서 처리한다.
- `html2pdf`는 입력 HTML 파일의 부모 경로를 기준으로 이미지 경로를 해석한다.
- `md2pdf`는 HTML 문자열과 함께 `md` 파일 부모 경로를 `base_dir`로 넘겨 일반 이미지 경로를 보존한다.
- `md2pdf` 종료 시 PDF 브라우저와 `helper_md_html._cleanup_browser()`를 둘 다 정리한다.
- 테스트에는 Chromium 사용 가능 여부를 먼저 확인하는 공통 helper를 둔다.

## 대상 파일

- 신규: `src/helper_md_doc/helper_html_pdf.py`
- 신규: `src/helper_md_doc/helper_md_pdf.py`
- 수정: `src/helper_md_doc/__init__.py`
- 수정: `pyproject.toml`
- 신규: `tests/test_html_to_pdf.py`
- 신규: `tests/test_md_to_pdf.py`

## 구현 메모

- 재사용: `helper_md_doc.helper_md_html.md_to_html`
- 재사용: `helper_md_doc.helper_html_doc.embed_images_as_base64`
- 재사용: `helper_md_doc.helper_md_html._cleanup_browser`
- 정리: PDF 구현은 필요 시 자체 브라우저 정리 함수를 둔다.
- 원칙: 신규 코드에는 `try/except`를 넣지 않고 실패 시 즉시 중단한다.
- 원칙: CLI는 얇게 유지하고 실제 변환은 함수 API에 둔다.

## 테스트 메모

- `html2pdf`: HTML 입력 시 PDF 생성 여부와 파일 크기 확인
- `md2pdf`: Markdown 입력 시 PDF 생성 여부와 파일 크기 확인
- 공통: 기본 출력 경로 규칙 확인
- 공통: 입력 파일 없음 처리 확인
- 공통: Chromium 사용 가능 여부 확인 helper 추가

## 진행 상태

- [x] 기존 `md2html` 구현 및 엔트리포인트 확인
- [x] 참고 소스의 PDF CLI 패턴 확인
- [x] `playwright` 기반 구현 방향 결정
- [x] `helper_html_pdf.py` 작성
- [x] `helper_md_pdf.py` 작성
- [x] `__init__.py` export 추가
- [x] `pyproject.toml` script 추가
- [x] `tests/test_html_to_pdf.py` 작성
- [x] `tests/test_md_to_pdf.py` 작성
- [x] 관련 테스트 실행

## 다음 작업

- 없음
