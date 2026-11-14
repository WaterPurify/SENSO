# 회귀 검사

## 자동 검사

GitHub Actions는 push/PR마다 아래 항목을 실행합니다.

- pytest: 기존 도메인·UI 검사, 실제 worker ZIP 내보내기와 계정 분리, 기존 계정 스키마 업그레이드, 두 세션의 비밀번호 변경·삭제 차단, 삭제 실패 후 재시도.
- 백업: age로 실제 암호화·복호화·복원, 파일 비교, 잘못된 키·변조 파일·경로 탈출·누락 사진 거부. `age`가 없는 로컬 환경에서는 해당 암호화 테스트만 건너뛰며, CI에는 age를 설치합니다.
- Ruff: `ruff check src tests ops`.
- Docker: 운영 이미지와 별도 백업 도구 이미지 빌드, 운영 uid 10001·pytest/ruff 미포함 검사.
- Chromium: 서로 다른 브라우저 세션 로그인, 390×844 화면의 ZIP 다운로드 및 내용 확인, 비밀번호 변경 후 다른 세션 로그아웃, 계정 삭제 후 두 세션 로그아웃.

기존 DB 마이그레이션의 실패 롤백 검사는 `tests/test_database.py`에 있습니다. 계정 테이블 변경은 기존 비밀번호를 유지하고 새 상태 열만 추가합니다. 과거 코드로의 무조건적인 롤백은 지원하지 않습니다. 복구 시 [운영 안내](ops/README.md)의 검증한 백업·복원 절차를 따르세요.

```bash
python -m pip install -r requirements-dev.txt
pytest -q
ruff check src tests ops
```

브라우저 테스트는 **새 임시 데이터 폴더에만** 실행하세요. 테스트 계정을 생성하고 마지막에 삭제합니다. CI의 `browser` 작업에 전체 실행 명령이 있습니다. `CHROMIUM_PATH`가 있으면 지정한 Chromium 실행 파일을, 없으면 Playwright가 설치한 Chromium을 사용합니다.

## 실제 기기 점검 — 아직 수행하지 않음

자동화한 390px 화면 검사는 실제 Android Chrome/iPhone Safari 검증이 아닙니다. 운영 공개 전에 다음을 두 기기에서 직접 확인하세요.

- [ ] Tailscale HTTPS 주소로 접속·가입·로그인
- [ ] 키보드 표시 시 입력칸과 저장 버튼 가림 여부
- [ ] 사진 선택·취소·저장 및 재접속 후 사진 표시
- [ ] ZIP 다운로드 후 파일 앱에서 압축 해제
- [ ] 한 기기에서 비밀번호 변경 시 다른 기기 로그인 만료
- [ ] 삭제 확인·실패 안내 및 화면 회전·뒤로 가기

Windows Docker Desktop에서의 PowerShell 실행도 운영자가 확인해야 합니다. 개발 검증 환경에서는 PowerShell 구문 검사, Linux Docker에서 별도 볼륨 백업·복원, Chromium 브라우저 검사를 수행합니다. 실제 운영 데이터와 사용자 PC 설정은 이 테스트가 변경하지 않습니다.
