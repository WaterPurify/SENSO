"""웹 응답에 보안 헤더를 붙이는 ASGI 미들웨어.

- 클릭재킹 방지: 다른 사이트가 SENSO를 <iframe> 안에 넣지 못하게 (frame-ancestors, X-Frame-Options)
- MIME 추측 금지, 바깥 링크로 나갈 때 주소(Referer) 보내지 않기
- 카메라·마이크·위치·결제 같은 브라우저 기능은 쓰지 않으므로 막아 둔다
- HTTPS로 접속했을 때(Tailscale 등) 다음부터 HTTPS만 쓰도록 (HTTP에서는 브라우저가 무시)

CSP는 Flutter 웹(Flet)이 쓰는 스크립트·WebAssembly를 막지 않도록, 스크립트와 상관없는 항목만 정한다.
WebSocket 연결에는 손대지 않는다.
"""

SECURITY_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (
        b"content-security-policy",
        b"frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'",
    ),
    (b"x-frame-options", b"DENY"),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (
        b"permissions-policy",
        b"camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
    ),
    (b"cross-origin-opener-policy", b"same-origin"),
    (b"strict-transport-security", b"max-age=31536000"),
)
_NAMES = {name for name, _ in SECURITY_HEADERS} | {b"server"}


class SecurityHeaders:
    """모든 HTTP 응답에 SECURITY_HEADERS를 붙이고, 서버 이름(Server 헤더)은 지운다."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message.get("type") == "http.response.start":
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() not in _NAMES]
                headers.extend(SECURITY_HEADERS)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)
