from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class PrivateResponseMiddleware:
    def __init__(self, app: ASGIApp, api_prefix: str) -> None:
        self.app = app
        self.prefixes = (f"{api_prefix}/auth", f"{api_prefix}/conversations")
        self.sources_prefix = f"{api_prefix}/sources"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        is_json_endpoint = path.startswith(self.prefixes)
        is_sources_endpoint = path == self.sources_prefix or path.startswith(
            f"{self.sources_prefix}/"
        )
        if scope["type"] != "http" or not (is_json_endpoint or is_sources_endpoint):
            await self.app(scope, receive, send)
            return
        if is_json_endpoint and scope.get("method") in {"POST", "PATCH", "PUT"}:
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > 131072:
                    response = JSONResponse(
                        status_code=413,
                        content={"code": "REQUEST_TOO_LARGE", "message": "请求过大", "details": []},
                        headers={"Cache-Control": "no-store"},
                    )
                    await response(scope, receive, send)
                    return
                if not message.get("more_body", False):
                    break
            delivered = False
            original_receive = receive

            async def buffered_receive() -> Message:
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await original_receive()

            receive = buffered_receive

        async def private_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"cache-control"
                ]
                message["headers"] = [*headers, (b"cache-control", b"no-store")]
            await send(message)

        await self.app(scope, receive, private_send)
