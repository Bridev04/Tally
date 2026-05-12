from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    def __init__(self, *, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def clear(self) -> None:
        self._requests.clear()

    def check(self, *, key: str) -> None:
        now = monotonic()
        request_times = self._requests[key]
        while request_times and request_times[0] <= now - self.window_seconds:
            request_times.popleft()

        if len(request_times) >= self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

        request_times.append(now)


def get_client_ip(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host
