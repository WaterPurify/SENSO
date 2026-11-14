"""웹 보안 헤더 미들웨어."""

import asyncio

from senso.web_security import SECURITY_HEADERS, SecurityHeaders


def run(app, scope):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(SecurityHeaders(app)(scope, receive, send))
    return sent


async def plain_app(scope, receive, send):
    if scope["type"] == "http":
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"text/html"),
                    (b"server", b"uvicorn"),
                    (b"X-Frame-Options", b"ALLOWALL"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})
    else:
        await send({"type": "websocket.accept"})


def test_http_response_gets_security_headers():
    sent = run(plain_app, {"type": "http", "path": "/"})
    headers = dict(sent[0]["headers"])
    for name, value in SECURITY_HEADERS:
        assert headers[name] == value
    assert b"frame-ancestors 'none'" in headers[b"content-security-policy"]
    assert headers[b"content-type"] == b"text/html"  # 원래 헤더는 그대로
    assert b"server" not in headers  # 서버 이름은 감춘다
    # 앱이 넣은 약한 값은 우리 값으로 바뀐다 (대소문자 상관없이 하나만)
    assert [k for k, _ in sent[0]["headers"] if k.lower() == b"x-frame-options"] == [
        b"x-frame-options"
    ]
    assert sent[1]["body"] == b"ok"


def test_websocket_untouched():
    sent = run(plain_app, {"type": "websocket", "path": "/ws"})
    assert sent == [{"type": "websocket.accept"}]
