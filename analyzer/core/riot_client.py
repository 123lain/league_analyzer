from typing import Any, Dict, List

import httpx
import asyncio

from analyzer.config import settings
from analyzer.core.logger import setup_logger
from analyzer.core.exceptions import RiotAPIError, ServiceConfigurationError
from analyzer.core.rate_limiter import RiotRateLimiter
from analyzer.schemas.riot import RiotPlayer, RankedEntry, RiotMatch


REGIONAL_HOST = 'https://europe.api.riotgames.com'  # account-v1, match-v5
PLATFORM_HOST = "https://euw1.api.riotgames.com"    # summoner-v4, league-v4

MAX_RETRIES = 3
BASE_NETWORK_DELAY = 1.5
MAX_429_ATTEMPTS = 10

logger = setup_logger()


class RiotAPIClient:
    def __init__(self):
        self.api_key = settings.RIOT_API_KEY
        if not self.api_key:
            logger.error("Riot API key not set")

        self.headers = {
            'X-Riot-Token': self.api_key,
            'Accept-Language': 'en-US,en;q=0.9'
        }

        self.timeout = httpx.Timeout(
            connect=5.0,
            read=15.0,
            write=5.0,
            pool=10.0
        )
        self.client: httpx.AsyncClient | None = None

        self.rate_limiter = RiotRateLimiter()
        self.connection_semaphore = asyncio.Semaphore(5)

    async def start(self):
        if not self.client:
            self.client = httpx.AsyncClient(
                headers=self.headers,
                timeout=self.timeout,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
            )
            logger.info('Starting async HTTPX client')

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info('Closing async HTTPX client')

    async def _request(
            self,
            method: str,
            path: str,
            params: Dict[str, Any] | None = None,
            host: str = REGIONAL_HOST,
    ) -> Dict[str, Any] | None:
        if not self.client:
            raise RuntimeError('Riot API client is not started')

        url = f'{host}{path}'

        for attempt in range(MAX_RETRIES):
            try:
                await self.rate_limiter.acquire()

                async with self.connection_semaphore:
                    response = await self.client.request(method, url, params=params)

                self.rate_limiter.update_from_headers(response.headers)
            except (httpx.TimeoutException, httpx.RequestError) as e:
                if attempt == MAX_RETRIES - 1:
                    logger.critical(f'Shutdown after {MAX_RETRIES} retries: {e}')
                    raise

                if isinstance(e, httpx.TimeoutException):
                    message = f'Request timeout: {e}'
                else:
                    message = f'Network error: {e}'

                delay = BASE_NETWORK_DELAY * (2 ** attempt)
                logger.warning(f'{message}. Retrying in {delay} seconds.')
                await asyncio.sleep(delay)
                continue

            # 429 handling
            rate_limit_attempts = 0
            while response.status_code == 429:
                rate_limit_attempts += 1
                if rate_limit_attempts > MAX_429_ATTEMPTS:
                    raise RiotAPIError('Maximum retries exceeded', status_code=429)

                retry_after = int(response.headers.get('Retry-After', 5))
                logger.warning(f'Rate limited. Sleeping for {retry_after} seconds..'
                               f'Attempt {rate_limit_attempts}/{MAX_429_ATTEMPTS}'
                               )

                await self.rate_limiter.handle_429(retry_after)
                await asyncio.sleep(retry_after)
                try:
                    await self.rate_limiter.acquire()
                    async with self.connection_semaphore:
                        response = await self.client.request(method, url, params=params)
                except (httpx.TimeoutException, httpx.RequestError) as e:
                    logger.warning(f'Error during 429 retry: {e}')
                    break

            # other errors
            if response.status_code == 401:
                logger.critical('Invalid/expired API key')
                raise ServiceConfigurationError('Invalid/expired API key. Shutting down.')

            if response.status_code == 403:
                logger.critical('Access denied')
                raise ServiceConfigurationError('Shutting down: Access denied')

            if response.status_code == 404:
                logger.info(f'Resource not found: {path}')
                return None


            # riot-side errors
            if response.status_code in (500, 502, 503, 504):
                if attempt == MAX_RETRIES - 1:
                    logger.error(
                        f"Server error {response.status_code} after {MAX_RETRIES} retries for {path}"
                    )
                    response.raise_for_status()

                delay = BASE_NETWORK_DELAY * (2 ** attempt)
                logger.warning(
                    f"Server error {response.status_code}, retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})"
                )

                await asyncio.sleep(delay)
                continue

            if response.status_code != 200:
                logger.error(f'Unexpected HTTP error {response.status_code} for path {path}')
                response.raise_for_status()

            return response.json()


    async def get_player_by_riot_id(
            self,
            game_name: str,
            tag_line: str
    ) -> RiotPlayer | None:
        """
        Fetch player puuid using given Riot ID (regional host)\n
        Endpoint: /riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}
        """
        path = f'/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}'

        return await self._request('GET', path)

    async def get_player_by_puuid(
            self,
            puuid: str
    ) -> RiotPlayer | None:
        """
        Fetch player puuid using given puuid (regional host)\n
        Endpoint: /riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}
        """
        path = f'/riot/account/v1/accounts/by-puuid/{puuid}'

        return await self._request('GET', path)


    async def get_ranked_entries(
            self,
            puuid: str
    ) -> List[RankedEntry] | None:
        """
        Fetch SoloQ and flex ranked entries for summoner (platform host)\n
        Endpoint: /lol/league/v4/entries/by-puuid/{puuid}
        """
        path = f'/lol/league/v4/entries/by-puuid/{puuid}'
        data = await self._request('GET', path, host=PLATFORM_HOST)
        return data if data else []

    async def get_recent_match_ids(
            self,
            puuid: str,
            count: int = 20,
            queue: int | None = None
    ) -> list[str] | None:
        """
        Fetch players recent matches' ids. Pass queue=420 to get SoloQ only (regional host)\n
        Endpoint: /lol/match/v5/matches/by-puuid/{puuid}/ids
        """
        path = f'/lol/match/v5/matches/by-puuid/{puuid}/ids'
        params: Dict[str, Any] = {
            'start': 0,
            'count': count
        }
        if queue is not None:
            params['queue'] = queue

        data = await self._request('GET', path, params=params)
        return data if data else []

    async def get_match_details(
            self,
            match_id: str
    ) -> RiotMatch | None:
        """
        Get full match details (regional host)\n
        Endpoint: /lol/match/v5/matches/{match_id}
        """
        path = f'/lol/match/v5/matches/{match_id}'
        return await self._request('GET', path)
