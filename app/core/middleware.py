from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, max_body_bytes: int) -> None:  # noqa: ANN001
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                size = int(content_length)
            except ValueError:
                return Response(status_code=status.HTTP_400_BAD_REQUEST)
            if size > self.max_body_bytes:
                return Response(
                    content="Request body too large.",
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    media_type="text/plain",
                )

        return await call_next(request)
