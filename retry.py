import asyncio
import logging

from telegram.error import TimedOut, NetworkError, RetryAfter, BadRequest

logger = logging.getLogger(__name__)


async def call_with_retry(func, *args, max_retries=5, delay=0.8, **kwargs):
    last_exc = None
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except BadRequest as e:
            raise e
        except RetryAfter as e:
            last_exc = e
            await asyncio.sleep(e.retry_after)
        except (TimedOut, NetworkError) as e:
            last_exc = e
            wait = delay * (attempt + 1)
            logger.warning(f"Сетевая ошибка, повтор {attempt + 1}/{max_retries}: {e}. Жду {wait}s")
            await asyncio.sleep(wait)
    raise last_exc