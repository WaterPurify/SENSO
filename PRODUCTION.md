# 운영(배포)용으로 실행하기

개발할 때는 지금처럼 `compose.yaml`(포트 8550)을 쓰고, 실제로 쓰거나 다른 사람에게 보여 줄 때는
운영용 `compose.prod.yaml`(포트 8551)을 씁니다. 두 개는 포트와 데이터가 따로라서 함께 켜도 섞이지 않습니다.

## 켜기·끄기

```bash
docker compose -f compose.prod.yaml up -d --build
```

브라우저에서 http://localhost:8551 을 엽니다. 이 PC에서만 접속됩니다.

```bash
docker compose -f compose.prod.yaml down
```

끄더라도 데이터는 Docker 볼륨 `senso-prod_data`에 남습니다. Docker Desktop을 다시 켜면 앱도 자동으로 다시 뜹니다.

코드를 고친 뒤에는 `up -d --build`를 다시 실행해야 반영됩니다(운영용은 소스 폴더를 연결하지 않습니다).

## 개발용과 무엇이 다른가

| | 개발용 (`compose.yaml`) | 운영용 (`compose.prod.yaml`) |
|---|---|---|
| 실행 사용자 | root | 일반 사용자 `senso` (uid 10001) |
| 파일 시스템 | 쓰기 가능, 소스 폴더 연결 | **읽기 전용**. 쓸 수 있는 곳은 `/data`(DB·사진)와 `/tmp`(64MB)뿐 |
| 코드 | PC의 폴더를 그대로 연결 | 이미지 안에 복사, 고칠 수 없음 |
| 개발 도구 | git, pytest, ruff, flet-cli | 없음 |
| 의존성 | `requirements-dev.txt` (일부 버전 범위) | `requirements.lock` — 31개 패키지 버전과 **해시 고정**. 내려받은 파일이 다르면 설치 실패 |
| 베이스 이미지 | `python:3.12-slim` | 같은 이미지를 **다이제스트로 고정** |
| 리눅스 특권 | 기본값 | 모두 제거(`cap_drop: ALL`), 권한 상승 금지(`no-new-privileges`) |
| 자원 제한 | 없음 | 메모리 768MB, CPU 2개, 프로세스 200개 |
| 상태 확인 | 없음 | 30초마다 응답 확인(HEALTHCHECK) |
| 로그 | 무제한 | 10MB × 3개까지 |
| 이미지 크기 | 약 629MB | 약 416MB |

이미지에 개인 데이터가 들어가지 않도록 `.dockerignore`가 `.data/` 폴더, `*.db` 파일, `.env`를 뺍니다.

## 백업과 복원

백업은 데이터 볼륨을 이 폴더의 `backup/`에 tar 파일로 저장합니다.

```bash
docker run --rm -v senso-prod_data:/data:ro -v "%cd%/backup:/backup" python:3.12-slim tar czf /backup/senso-data.tgz -C /data .
```

- PowerShell에서는 `%cd%` 대신 `${PWD}`를 씁니다.
- 백업 파일에는 모든 계정의 기록과 사진이 들어 있습니다. 안전한 곳에 두고, 저장소(GitHub)에 올리지 마세요.

복원은 앱을 끈 상태에서 합니다. 볼륨의 기존 내용을 덮어씁니다.

```bash
docker run --rm -v senso-prod_data:/data -v "%cd%/backup:/backup" python:3.12-slim sh -c "tar xzf /backup/senso-data.tgz -C /data && chown -R 10001:10001 /data"
```

## 의존성·베이스 이미지 갱신

`requirements.in`의 버전을 바꾼 뒤, 아래 명령으로 `requirements.lock`(해시 포함)을 다시 만듭니다. 리눅스 이미지와 같은 환경에서 만들어야 해시가 맞습니다.

```bash
docker run --rm -v "%cd%:/work" -w /work python:3.12-slim sh -c "pip install -q pip-tools && pip-compile --generate-hashes --allow-unsafe --strip-extras --no-header -o requirements.lock requirements.in"
```

베이스 이미지를 새로 받으려면 `docker pull python:3.12-slim`으로 받은 뒤 아래 명령으로 다이제스트를 확인하고, `Dockerfile.prod`의 `FROM` 줄을 바꿉니다.

```bash
docker image inspect python:3.12-slim --format "{{index .RepoDigests 0}}"
```

갱신한 뒤에는 테스트(`docker compose run --rm test`)와 운영용 빌드를 다시 확인합니다.

## 아직 남은 2단계 작업

- **HTTPS**: 지금은 `127.0.0.1`에서만 열려 있어 괜찮습니다. 폰이나 집 밖에서 접속하려면 HTTPS를 붙여야 합니다(Tailscale, Caddy, Cloudflare Tunnel 중 선택).
- **저장 데이터 암호화**: Windows 11 Home에서는 "설정 → 개인 정보 및 보안 → 장치 암호화"(지원하는 PC만)를 켭니다. Docker 볼륨은 WSL 디스크 파일 안에 있으므로 PC 디스크가 암호화되면 함께 보호됩니다.
