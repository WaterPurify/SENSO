# SENSO 개발 환경: Python 3.12 + Flet(웹 모드) + 테스트 도구
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src \
    SENSO_DATA_DIR=/data \
    SENSO_TZ=Asia/Seoul \
    FLET_FORCE_WEB_SERVER=true \
    FLET_SERVER_IP=0.0.0.0 \
    FLET_SERVER_PORT=8550

# VS Code Dev Container에서 Git을 쓰기 위해 필요
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성만 먼저 설치해, 코드가 바뀌어도 이 단계는 캐시를 재사용한다
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

COPY . .

EXPOSE 8550

# 웹 모드로 실행 (FLET_FORCE_WEB_SERVER). 코드를 고친 뒤에는 컨테이너를 다시 시작한다
CMD ["python", "src/main.py"]
