# 운영(배포)용으로 실행하기

개발할 때는 지금처럼 `compose.yaml`(포트 8550)을 쓰고, 실제로 쓰거나 다른 사람에게 보여 줄 때는
운영용 `compose.prod.yaml`(포트 8551)을 씁니다. 두 개는 포트와 데이터가 따로라서 함께 켜도 섞이지 않습니다.

## 켜기·끄기

```bash
docker compose -f compose.prod.yaml up -d --build
```

브라우저에서 http://localhost:8551 을 엽니다. 내 폰이나 집 밖에서는 Tailscale 주소(https://senso.<내 tailnet>.ts.net)로 접속합니다. 아래 "Tailscale로 HTTPS"를 참고하세요.

화면 맨 아래(첫 화면, "나" 탭)의 `v0.8.0 · 빌드 …` 표시로 새 코드가 올라갔는지 확인할 수 있습니다. 운영용은 소스 코드 지문(`코드 abc1234`)을 보여 주며, 코드가 바뀌면 값이 바뀝니다.

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

## Tailscale로 HTTPS (내 폰·집 밖에서 접속)

운영용을 켜면 `ts`(Tailscale) 컨테이너가 앱과 함께 뜹니다.
- **누가 접속할 수 있나:** 내 Tailscale 계정에 로그인한 기기에서만 `https://senso.<내 tailnet>.ts.net`으로 접속할 수 있습니다.
- **인터넷 공개 여부:** 인터넷 전체에는 공개하지 않습니다(Funnel 꺼짐). 공유기 포트도 열지 않습니다.
- **암호화:** 연결은 Tailscale(WireGuard)과 HTTPS 인증서로 두 번 암호화됩니다.
- **이 PC에서 접속:** 지금처럼 http://localhost:8551 로도 됩니다.
- **앱과의 관계:** 앱과 Tailscale은 네트워크를 따로 쓰므로, Tailscale이 멈추거나 다시 시작돼도 이 PC에서의 접속(8551)에는 영향이 없습니다.

### 처음 한 번 설정 (10분 정도)

1. **Tailscale 계정 만들기:** https://login.tailscale.com 에서 구글 계정 등으로 가입합니다(개인용 무료).
2. **HTTPS 인증서 켜기:** 관리 화면의 DNS 메뉴(https://login.tailscale.com/admin/dns)에서 **MagicDNS**가 켜져 있는지 확인하고, 아래쪽 **HTTPS Certificates → Enable HTTPS**를 누릅니다.
3. **인증 키 만들기:** 관리 화면 **Settings → Keys → Generate auth key**를 누릅니다. Reusable은 끄고 그대로 만든 뒤, `tskey-auth-...`로 시작하는 키를 복사합니다. 키는 한 번만 보이니 바로 다음 단계로 넘어가세요.
4. **키를 `.env`에 넣기:** 이 폴더(`SENSO/app`)에 `.env` 파일을 만들고 한 줄을 적습니다.
   ```
   TS_AUTHKEY=tskey-auth-여기에-복사한-키
   ```
   `.env`는 `.gitignore`에 들어 있어 GitHub에 올라가지 않습니다. 키는 처음 로그인할 때 한 번만 쓰이고, 로그인 정보는 `senso-prod_ts-state` 볼륨에 남습니다. 로그인이 끝나면 `.env`에서 키를 지워도 됩니다.
5. **켜기:**
   ```bash
   docker compose -f compose.prod.yaml up -d
   ```
6. **주소 확인:** 관리 화면의 Machines에 `senso`가 보이면 성공입니다. 접속 주소는 아래 명령으로도 확인할 수 있습니다.
   ```bash
   docker compose -f compose.prod.yaml exec ts tailscale status --self
   ```
7. **폰에서 접속:** 폰에 Tailscale 앱(앱스토어·플레이스토어)을 설치해 같은 계정으로 로그인한 뒤, `https://senso.<내 tailnet>.ts.net`을 엽니다. 처음 접속할 때 인증서를 받느라 몇 초 걸릴 수 있습니다.

### 알아 둘 점

- **키 없이 켰을 때:** 인증 키 없이 켜면 Tailscale 컨테이너가 로그에 로그인 링크를 띄우고 1분마다 다시 시작합니다(링크도 바뀜). 계정이 이미 있다면 `docker compose -f compose.prod.yaml logs --tail 5 ts`로 가장 최근 링크를 바로 열어 로그인해도 됩니다.
- **로그인 만료:** Tailscale 로그인은 기본 180일 뒤 만료됩니다. 관리 화면의 Machines → senso → **Disable key expiry**를 켜면 계속 유지됩니다.
- **로그인 제한:** Tailscale을 거쳐 들어오면 앱에는 모든 접속이 Tailscale 컨테이너 주소 하나로 보입니다. 그래서 접속 주소별 로그인 제한은 사실상 하나로 묶입니다. 내 기기만 들어오는 구조라 큰 문제는 아니고, 아이디별·전체 제한은 그대로 동작합니다.
- **끄기:** Tailscale을 끄려면 `docker compose -f compose.prod.yaml down`으로 앱과 함께 끄거나, 관리 화면에서 `senso` 기기를 지웁니다.

## 아직 남은 2단계 작업

- **저장 데이터 암호화**: Windows 11 Home에서는 "설정 → 개인 정보 및 보안 → 장치 암호화"(지원하는 PC만)를 켭니다. Docker 볼륨은 WSL 디스크 파일 안에 있으므로 PC 디스크가 암호화되면 함께 보호됩니다.
