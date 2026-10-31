"""AI for Thai adapter. Credentials and draft text never go into logs."""
import asyncio
from collections import OrderedDict
import hashlib
import os
from pathlib import Path
import secrets
import time
from urllib.parse import urlsplit

import httpx
from dotenv import dotenv_values


class ModerationUnavailable(Exception):
    pass


class BullyingModerator:
    def __init__(self, *, api_key, service_url, transport=None):
        self.api_key = api_key
        self.service_url = service_url
        self.http = httpx.AsyncClient(timeout=8, follow_redirects=False, transport=transport)
        self.slots = asyncio.Semaphore(8)
        self.cache = OrderedDict()
        self.salt = secrets.token_bytes(32)

    @classmethod
    def from_env(cls):
        # Resolve root independently of cwd, including python backend/main.py.
        config = dotenv_values(Path(__file__).resolve().parents[1] / '.env', encoding='utf-8-sig')
        return cls(api_key=os.getenv('API_KEY', config.get('API_KEY', '')),
                   service_url=os.getenv('SERVICE_URL', config.get('SERVICE_URL', '')))

    @staticmethod
    def parse(payload):
        value = payload.get('bully_type') if isinstance(payload, dict) else None
        # The real service returns 0 for neutral text but a list for detected types.
        if isinstance(value, list) and value:
            verdicts = [BullyingModerator.parse({'bully_type': item}) for item in value]
            return all(verdicts)
        if type(value) is int and 0 <= value <= 6:
            return value == 0
        if isinstance(value, str) and value in tuple(str(i) for i in range(7)):
            return value == '0'
        raise ModerationUnavailable('Invalid moderation response')

    async def check(self, text):
        if not self.api_key or not self.service_url:
            raise ModerationUnavailable('Missing moderation configuration')
        try:
            url = urlsplit(self.service_url)
            if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ('127.0.0.1', 'localhost')):
                raise ModerationUnavailable('HTTPS is required')
            key = hashlib.blake2b(text.encode('utf-8'), key=self.salt).digest()
            now = time.monotonic()
            for old_key, (expires, _) in list(self.cache.items()):
                if expires <= now:
                    del self.cache[old_key]
            if key in self.cache:
                return self.cache[key][1]
            async with asyncio.timeout(10):
                async with self.slots:
                    response = await self.http.post(self.service_url,
                        headers={'Apikey': self.api_key}, data={'text': text})
                    response.raise_for_status()
                    allowed = self.parse(response.json())
            # Only a salted digest and verdict are retained, for 30 seconds.
            self.cache[key] = (time.monotonic() + 30, allowed)
            while len(self.cache) > 256:
                self.cache.popitem(last=False)
            return allowed
        except (httpx.HTTPError, ValueError, TimeoutError):
            raise ModerationUnavailable('Moderation service unavailable') from None

    async def close(self):
        self.cache.clear()
        await self.http.aclose()
