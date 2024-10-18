import asyncio

from web3 import AsyncWeb3
from eth_typing import BlockNumber

from .config import (
    ChainConfig,
    MAX_DELAY_PER_BLOCK_BATCH,
    BATCH_BLOCK_NUMBER_SIZE,
    CHAINS_CONFIG,
)
from .db.transfer import get_pending_transfers_block_number, to_finalized, to_reorg
from .utils import async_web3_factory, filter_blocks


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


if __name__ == "__main__":
    asyncio.run(update_finalized_transfers(CHAINS_CONFIG["11155111"]))
