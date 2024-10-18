import asyncio
import time
from typing import Any, Callable, Coroutine, Iterable, TypeVar

from eth_typing import BlockNumber
from web3 import AsyncWeb3, AsyncHTTPProvider

from .config import MAX_DELAY_PER_BLOCK_BATCH, ChainConfig

T = TypeVar("T")


async def async_web3_factory(chain: ChainConfig) -> AsyncWeb3:
    w3 = AsyncWeb3(AsyncHTTPProvider(chain.private_rpc))
    return w3


async def _filter_blocks(
    w3: AsyncWeb3,
    blocks: Iterable[BlockNumber],
    fn: Callable[..., Coroutine[Any, Any, list[T]]],
    **kwargs,
) -> list[T]:
    tasks = [asyncio.create_task(fn(w3, BlockNumber(i), **kwargs)) for i in blocks]
    result = []
    for task in tasks:
        result.extend(await task)
    return result


async def filter_blocks(
    w3,
    blocks_number: Iterable[BlockNumber],
    fn: Callable[..., Coroutine[Any, Any, list[T]]],
    **kwargs,
) -> list[T]:
    start = time.time()
    result = await _filter_blocks(w3, blocks_number, fn, **kwargs)
    end = time.time()
    await asyncio.sleep(max(MAX_DELAY_PER_BLOCK_BATCH - end - start, 0))
    return result
