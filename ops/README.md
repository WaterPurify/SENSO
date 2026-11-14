# 운영자 백업·복원 (Windows PowerShell)

이 도구는 앱의 **내 데이터 내보내기 ZIP**과 다릅니다. ZIP은 로그인한 한 사람의 기록과 사진이며, 계정 정보와 자동 복원 기능이 없습니다. 운영 백업은 `accounts.db`와 모든 사용자 DB·사진을 포함한 **age 암호화 파일**입니다. Tailscale 상태 볼륨·`.env`·인증 키는 포함하지 않습니다.

백업은 앱을 잠시 정지하고 파일을 읽습니다. 백업 성공·실패와 관계없이, 시작 전에 실행 중이었던 앱만 다시 시작합니다. 데이터 볼륨을 사용하는 다른 컨테이너가 있으면 중단합니다. 백업 중 다른 운영자가 앱을 시작하거나 볼륨을 수정하지 않도록 하세요. 원본 볼륨은 읽기 전용으로 연결합니다.

## 1. 복구 키 준비 (처음 한 번)

Docker Desktop을 켜고 저장소 루트에서 실행합니다. 키는 저장소나 OneDrive 프로젝트 폴더 밖에 두세요. 아래 명령은 기존 키 파일을 덮어쓰지 않습니다.

```powershell
docker build -f ops/Dockerfile -t senso-backup:local .
$keyDir = Join-Path $env:USERPROFILE '.senso-backup-keys'
New-Item -ItemType Directory -Force $keyDir | Out-Null
docker run --rm --network none --mount "type=bind,source=$keyDir,target=/keys" --entrypoint age-keygen senso-backup:local -o /keys/identity.txt
$identity = Join-Path $keyDir 'identity.txt'
$recipient = docker run --rm --network none --mount "type=bind,source=$keyDir,target=/keys,readonly" --entrypoint age-keygen senso-backup:local -y /keys/identity.txt
```

`$recipient`는 `age1...` 형태의 **공개키**여서 명령 인자로 써도 됩니다. `identity.txt`는 복호화용 **비밀키**입니다. 스크립트는 키 내용을 명령 인자·환경 변수·이미지에 넣지 않고, 실행 중인 도구 컨테이너에 파일로 읽기 전용 연결합니다. 비밀키는 백업과 별도 장소에도 안전하게 보관하세요. 키를 잃으면 복원할 수 없습니다. 키 파일에 대한 Windows 접근 권한을 본인으로 제한하고, PC의 BitLocker/장치 암호화도 유지하세요.

## 2. 백업 및 검증

```powershell
.\ops\backup.ps1 -Action Backup -Identity $identity -Recipient $recipient
```

`backup/senso-날짜-시간.tar.age`가 만들어집니다. 평문 tar 파일은 만들지 않습니다. 암호화 후 다시 복호화 스트림을 읽어 전체 파일 목록·크기·SHA-256·age 인증 태그를 확인한 경우에만 최종 파일명으로 저장합니다. 공간 부족, 누락된 사진, 손상된 SQLite DB 등은 실패로 처리합니다. 이미 있는 백업 파일을 덮어쓰지 않습니다.

```powershell
.\ops\backup.ps1 -Action Verify -Identity $identity -File 'senso-20261114-120000.tar.age'
```

검증은 암호화·파일 무결성을 확인합니다. 앱으로 실제 로그인하고 기록을 확인하는 복원 점검은 별도로 필요합니다. 정기 백업과 별도 저장 장치 보관은 운영자가 일정에 맞춰 실행해야 하며 이 변경에서 자동 스케줄러는 설치하지 않습니다. age 암호화는 발신자 서명이 아니므로 백업 파일의 출처도 관리하세요.

## 3. 새 볼륨으로 복원

```powershell
.\ops\backup.ps1 -Action Restore -Identity $identity -File 'senso-20261114-120000.tar.age' -RestoreVolume 'senso-restore-20261114'
```

반드시 새 `senso-restore-...` 이름을 사용합니다. 기존 볼륨은 거부합니다. 복원은 파일 해시, SQLite integrity/외래 키, 지원 스키마(현재 1~7), 사진 참조를 검증합니다. 실패하면 새 볼륨의 불완전한 파일을 제거하고 오류를 반환합니다. 원래 운영 볼륨과 실행 중인 앱은 바꾸지 않습니다. 복원 파일은 uid/gid 10001, 폴더 700·파일 600으로 설정합니다.

시험 서버를 별도 포트로 열어 로그인·기록·사진·ZIP 내보내기를 확인합니다. 이 서버의 데이터는 복원한 복사본입니다.

```powershell
docker run -d --name senso-restore-check --read-only --tmpfs /tmp:size=64m,mode=1777 --user 10001:10001 --cap-drop ALL --security-opt no-new-privileges:true -p 127.0.0.1:8552:8550 --mount type=volume,source=senso-restore-20261114,target=/data senso-prod:latest
# http://localhost:8552 에서 확인
docker stop senso-restore-check
docker rm senso-restore-check
```

운영 전환은 검증 뒤 별도로 수행합니다. 다음 파일을 `compose.restore.yaml`로 만들고(볼륨명은 실제 이름으로 변경), 운영 앱을 중지한 다음 실행하세요.

```yaml
volumes:
  data:
    external: true
    name: senso-restore-20261114
```

```powershell
docker compose -f compose.prod.yaml stop app
docker compose -f compose.prod.yaml -f compose.restore.yaml up -d --no-deps --force-recreate app
```

이후 운영 명령에 두 Compose 파일을 계속 사용해야 합니다. `backup.ps1`은 실행 중인 `app` 컨테이너의 실제 `/data` 마운트를 찾아 백업합니다. 원래 볼륨은 삭제하지 마세요. 원래 볼륨으로 돌아가려면 복원 앱을 중지하고 기본 `compose.prod.yaml`만으로 다시 생성합니다. 전환 뒤 새로 쓴 기록은 이전 볼륨으로 자동 합쳐지지 않습니다.

**복원 시점의 계정과 비밀번호가 함께 돌아옵니다.** 백업 이후 삭제한 계정도 복원될 수 있으므로 삭제 요청 및 비밀번호 변경 이력을 확인한 뒤 서비스를 다시 열어야 합니다. 백업 보관 기한과 폐기 정책도 정하세요. 원본 데이터 볼륨 자체의 암호화는 이 도구가 설정하지 않습니다.

## 계정 삭제 실패 재시도

삭제 실패 시 계정은 `deleting=1`로 남아 로그인과 데이터 접근이 차단됩니다. 모든 앱 프로세스를 정지한 뒤 관리자 명령으로 재시도합니다. `USER_UUID`는 목록에서 확인한 실제 값으로 바꾸세요.

```powershell
docker compose -f compose.prod.yaml stop app
docker compose -f compose.prod.yaml run --rm --no-deps app python -m senso.maintenance list-deletions
docker compose -f compose.prod.yaml run --rm --no-deps app python -m senso.maintenance finish-deletion USER_UUID
docker compose -f compose.prod.yaml start app
```

복원 볼륨을 운영 중이면 위 명령에도 `-f compose.restore.yaml`을 추가합니다. 파일 잠금·권한·디스크 오류를 해결한 뒤 재시도하세요. 앱 버전을 되돌리더라도 새 계정 스키마를 모르는 과거 버전은 삭제 차단을 우회할 수 있으므로, 이전 코드만 단독으로 되돌리지 말고 검증한 백업과 함께 복구하세요.
