"""SENSO 진입점: Docker에서는 제한된 웹 서버, 그 밖에서는 데스크톱 앱."""

import os
from pathlib import Path

import flet as ft

from senso.app import main
from senso.photos import MAX_INPUT_BYTES
from senso.web_security import SecurityHeaders

if __name__ == "__main__":
    if os.getenv("FLET_FORCE_WEB_SERVER", "").lower() == "true":
        import flet_web.fastapi
        import uvicorn

        # FilePicker(with_data=True)는 WebSocket으로 파일을 보낸다.
        # 파싱 전에 전송 크기를 제한한다 (파일 20MB + 메시지 메타데이터 여유).
        web_app = flet_web.fastapi.app(
            main, assets_dir=str(Path(__file__).parent / "assets"), no_cdn=True
        )
        uvicorn.run(
            SecurityHeaders(web_app),  # 클릭재킹 방지 등 보안 헤더 (senso/web_security.py)
            host=os.getenv("FLET_SERVER_IP", "127.0.0.1"),
            port=int(os.getenv("FLET_SERVER_PORT", "8550")),
            ws="websockets-sansio",
            ws_max_size=MAX_INPUT_BYTES + 1024 * 1024,
            server_header=False,
        )
    else:
        ft.run(main)
