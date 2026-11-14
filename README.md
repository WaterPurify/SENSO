<p align="center">
  <img src="src/assets/characters/duo.png" alt="Sen & So" width="220">
</p>

<h1 align="center">SENSO</h1>

<p align="center">
  <b>Sen & So와 함께 찾는 나만의 커피·차 한 잔</b><br>
  커피를 좋아하는 <b>Sen</b>, 차를 좋아하는 <b>So</b>와 함께 한 잔을 기록하고, 다음 한 잔을 더 맛있게.
</p>

---

## 무엇을 할 수 있나요

| | 기능 |
|---|---|
| ☕ 원두·차 등록 | 이름, 산지(국기 표시), 로스터리·브랜드, 로스팅 정도·차 종류, 사진 |
| 📝 추출·시음 기록 | 원두량·물·온도·시간 같은 추출 조건과 산미·쓴맛·단맛·바디·만족도 평가 |
| 🔁 다음 레시피 추천 | 한 번에 한 조건만 바꾸는 규칙 기반 제안, 이전 기록과 비교, "이 레시피로 새 기록" |
| 🧭 취향 유형 테스트 | 12문항으로 8가지 유형 중 하나, 결과 카드 이미지 저장 |
| 🧬 Taste DNA | 만족도를 매긴 기록 5개 이상이면 내가 좋아하는 맛의 방향을 근거와 함께 표시 |
| 📖 오늘의 말씀 한 잔 | 원하는 사람만 켜는 기능. 기분을 고르면 어울리는 한 잔과 성경 말씀 한 구절 카드 |
| 🔐 계정 | 계정마다 기록·사진을 따로 보관 |

## 실행하기

Docker Desktop을 켠 뒤 아래 명령을 실행하고, 브라우저에서 http://localhost:8550 을 엽니다.

```bash
docker compose up -d --build app
```

테스트는 아래 명령으로 실행합니다.

```bash
docker compose run --rm test
```

Docker 없이 실행하려면 Python 3.12 가상환경에서 `pip install -r requirements-dev.txt`를 실행한 뒤 VS Code에서 F5를 누릅니다.

## 문서

- [PROJECT_PLAN.md](PROJECT_PLAN.md): 8주 개발 계획과 진행 상황
- [SECURITY_AND_SETUP.md](SECURITY_AND_SETUP.md): 로그인, 데이터 보관 위치, 기존 기록 가져오기

## 기술

Python 3.12 · [Flet](https://flet.dev) (Flutter UI) · SQLite · Pillow · pytest · Ruff

글꼴: [Pretendard](https://github.com/orioncactus/pretendard) (SIL Open Font License 1.1)
