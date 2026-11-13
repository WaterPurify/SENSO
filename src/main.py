"""SENSO 앱 진입점.

- Docker 컨테이너 안: Dockerfile의 FLET_FORCE_WEB_SERVER 설정으로 웹 서버로 실행된다.
  브라우저에서 http://localhost:8550 을 연다.
- 그 밖(PC의 .venv): 데스크톱 창으로 실행된다.
"""

import flet as ft

from senso.app import main

if __name__ == "__main__":
    ft.run(main)
