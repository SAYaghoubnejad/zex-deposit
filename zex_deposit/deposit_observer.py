import asyncio
import time
from typing import Callable, Iterable, TypeVar, Coroutine, Any

from web3 import AsyncWeb3, AsyncHTTPProvider
from eth_typing import BlockNumber, ChecksumAddress, ChainId

from utils.transfer_decoder import (
    decode_transfer_tx,
    NotRecognizedSolidityFuncError,
)
from db.models import Transfer, TransferStatus
from db.transfer import (
    get_latest_block_observed,
    insert_many_transfers,
    get_pending_transfers_block_number,
    to_finalized,
    to_reorg,
)
from db.address import insert_new_adderss_to_db, get_active_address
from config import (
    BATCH_BLOCK_NUMBER_SIZE,
    MAX_DELAY_PER_BLOCK_BATCH,
    CHAINS_CONFIG,
    ChainConfig,
)


T = TypeVar("T")


async def async_web3_factory(chain: ChainConfig) -> AsyncWeb3:
    w3 = AsyncWeb3(AsyncHTTPProvider(chain.private_rpc))
    return w3


async def get_block_batches(
    from_block: BlockNumber | int, latest_block: BlockNumber | int
) -> list[tuple[BlockNumber, ...]]:
    block_batches = [
        tuple(
            BlockNumber(j)
            for j in range(i, min(latest_block + 1, i + BATCH_BLOCK_NUMBER_SIZE + 1))
        )
        for i in range(from_block, latest_block + 1, BATCH_BLOCK_NUMBER_SIZE)
    ]
    return block_batches


async def extract_transfer_from_block(
    w3: AsyncWeb3, block_number: BlockNumber, chain_id: ChainId, **kwargs
) -> list[Transfer]:
    print(f"Observing block number {block_number} start")
    block = await w3.eth.get_block(block_number, full_transactions=True)
    result = []
    for tx in block.transactions:  # type: ignore
        try:
            decoded_input = decode_transfer_tx(tx.input.hex())
            result.append(
                Transfer(
                    tx_hash=tx.hash.hex(),
                    block_number=block_number,
                    chain_id=chain_id,
                    to=decoded_input._to,
                    value=decoded_input._value,
                    status=TransferStatus.PENDING,
                    token=tx.to,
                )
            )
        except NotRecognizedSolidityFuncError as _:
            ...
    print(f"Observing block number {block_number} end")
    return result


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


async def filter_transfers(
    transfers: list[Transfer], valid_addresses: set[ChecksumAddress]
) -> tuple[Transfer, ...]:
    return tuple(filter(lambda transfer: transfer.to in valid_addresses, transfers))


async def get_block_tx_hash(w3: AsyncWeb3, block_number: BlockNumber, **kwargs):
    block = await w3.eth.get_block(block_number)
    return [tx_hash.hex() for tx_hash in block.transactions]  # type: ignore


async def get_finalized_block_number(w3: AsyncWeb3) -> BlockNumber:
    finalized_block = await w3.eth.get_block("finalized")
    return finalized_block.number  # type: ignore


async def update_finalized_transfers(chain: ChainConfig):
    while True:
        w3 = await async_web3_factory(chain)
        finalized_block_number = await get_finalized_block_number(w3)
        pending_block_numbers = await get_pending_transfers_block_number(
            chain_id=chain.chain_id, finalized_block_number=finalized_block_number
        )

        if len(pending_block_numbers) == 0:
            print(
                f"No pending tx has been found. finalized_block_number: {finalized_block_number}"
            )
            await asyncio.sleep(MAX_DELAY_PER_BLOCK_BATCH)
            continue

        for i in range(len(pending_block_numbers)):
            blocks_to_check = pending_block_numbers[
                (i * BATCH_BLOCK_NUMBER_SIZE) : (i * (BATCH_BLOCK_NUMBER_SIZE + 1) + 1)
            ]
            results = await filter_blocks(
                w3,
                blocks_to_check,
                get_block_tx_hash,
            )
            await to_finalized(finalized_block_number, results)
            await to_reorg(min(blocks_to_check), max(blocks_to_check), results)


async def observe_deposit(chain: ChainConfig):
    last_block_observed = await get_latest_block_observed(chain.chain_id)
    while True:
        await insert_new_adderss_to_db()
        w3 = await async_web3_factory(chain)
        latest_block = await w3.eth.get_block_number()
        if last_block_observed is not None and last_block_observed == latest_block:
            print("block already observed continue")
            await asyncio.sleep(MAX_DELAY_PER_BLOCK_BATCH)
            continue
        elif last_block_observed is None:
            last_block_observed = latest_block
        block_batches = await get_block_batches(last_block_observed, latest_block)
        for blocks_number in block_batches:
            transfers = await filter_blocks(
                w3, blocks_number, extract_transfer_from_block, chain_id=chain.chain_id
            )
            valid_addresses = await get_active_address()
            valid_transfers = await filter_transfers(transfers, valid_addresses)
            print(list(valid_transfers))
            if len(valid_transfers) != 0:
                await insert_many_transfers(valid_transfers)
        last_block_observed = latest_block + 1


if __name__ == "__main__":
    asyncio.run(update_finalized_transfers(CHAINS_CONFIG["11155111"]))
