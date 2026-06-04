import asyncio
import time

from analyzer.settings.logger import setup_logger

logger = setup_logger()


class AsyncTokenBucket:
    def __init__(
            self,
            max_tokens:int,
            refill_rate: float
    ):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.tokens = float(max_tokens)
        self.last_refill_time = time.monotonic()

        self._lock = asyncio.Lock()
        self._paused_until = 0.0

    async def _refill(self):
        """
        Refill bucket with tokens based on time passed
        """
        now = time.monotonic()

        # if frozen from a 429
        if now < self._paused_until:
            return

        elapsed = now - self.last_refill_time
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)

        self.last_refill_time = now

    async def wait_for_token(self):
        """
        Asking permission to send a request. Sleeps if bucket is empty
        """
        while True:
            async with self._lock:
                await self._refill()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return

                sleep_time = (1.0 - self.tokens) / self.refill_rate

            await asyncio.sleep(sleep_time)

    async def update_retry_after(
            self,
            retry_after: float
    ):
        """
        If we catch a 429, empty the bucket and freeze it for specified time
        """
        async with self._lock:
            logger.warning(f'Caught a 429 error. Freezing for  {retry_after} seconds')
            self.tokens = 0.0
            self._paused_until = time.monotonic() + retry_after


class RiotRateLimiter:
    def __init__(self):
        self.app = AsyncTokenBucket(max_tokens=20, refill_rate=20)
        self.method = AsyncTokenBucket(max_tokens=10, refill_rate=10)

    def _parse_limits(self, header: str):
        """
        Parse limits from header
        """
        limits = []
        for part in header.split(","):
            if part:
                count, window = part.split(":")
                limits.append((int(count), int(window)))
        return limits

    async def handle_429(
            self,
            retry_after:float
    ):
        await self.app.update_retry_after(retry_after)
        await self.method.update_retry_after(retry_after)

    def update_from_headers(
            self,
            headers: dict
    ):
        """
        Sync with Riot headers limits
        """
        app = headers.get('X-App-Rate-Limit')
        method = headers.get('X-Method-Rate-Limit')

        if app:
            max_tokens, window = self._parse_limits(app)[0]
            self.app.max_tokens = max_tokens
            self.app.refill_rate = max_tokens / window

        if method:
            max_tokens, window = self._parse_limits(method)[0]
            self.method.max_tokens = max_tokens
            self.method.refill_rate = max_tokens / window

    async def acquire(self):
        """
        call before the request
        """
        await self.app.wait_for_token()
        await self.method.wait_for_token()